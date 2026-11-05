import os
import joblib
import numpy as np
import rasterio
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from scipy.ndimage import binary_erosion
from core.data import BaseProcessor
from geoserver_utils import publish_water_layer
import time


class MappingProcessor(BaseProcessor):
    def __init__(self, model_path, output_dir, param_name="chla", combinations=None):
        self.model = joblib.load(model_path)
        self.output_dir = os.environ.get(
            'GEOSERVER_RASTER_DIR',
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'tools', 'geoserver', 'data_dir', 'rasters')
        )
        self.param_name = param_name

        self.SELECTED_COMBINATIONS = combinations or [
            "Rrs_620-Rrs_665", "Rrs_665-Rrs_682", "Rrs_400", "Rrs_412",
            "((Rrs_412 * Rrs_443) / Rrs_709)", "(Rrs_400 * Rrs_412)",
            "Rrs_665/Rrs_674", "Rrs_665/Rrs_682",
            "(Rrs_665-Rrs_674)/(Rrs_665 + Rrs_674)",
            "(Rrs_665-Rrs_682)/(Rrs_665 + Rrs_682)"
        ]

    def process(self, data):
        tif_path = data.path
        os.makedirs(self.output_dir, exist_ok=True)

        with rasterio.open(tif_path) as src:
            band_dict = {
                desc: src.read(i + 1).astype("float32")
                for i, desc in enumerate(src.descriptions) if desc is not None
            }
            profile = src.profile

            print(f"📦 Mapping 已加载波段: {list(band_dict.keys())}")

            features = []
            try:
                for expr in self.SELECTED_COMBINATIONS:
                    with np.errstate(divide='ignore', invalid='ignore'):
                        val = eval(expr, {"__builtins__": None}, band_dict)
                    features.append(val)
            except Exception as e:
                raise Exception(f"❌ Mapping公式计算失败: {e}")

            features_stack = np.stack(features, axis=-1)
            rows, cols, fnum = features_stack.shape
            X = features_stack.reshape(-1, fnum)

            mask_valid = np.all(np.isfinite(X), axis=1)
            y_pred = np.full(X.shape[0], np.nan)

            if np.any(mask_valid):
                y_pred[mask_valid] = self.model.predict(X[mask_valid])

            result_map = y_pred.reshape(rows, cols)

            water_mask = np.isfinite(result_map)
            if np.any(water_mask):
                eroded_mask = binary_erosion(water_mask, iterations=1)
                result_map[~eroded_mask] = np.nan

            valid_values = result_map[np.isfinite(result_map)]
            valid_pixel_count = valid_values.size

            if valid_pixel_count > 0:
                v_min, v_max = np.nanpercentile(valid_values, [2, 98])
                if v_min == v_max:
                    v_min, v_max = float(np.min(valid_values)), float(np.max(valid_values))
                    if v_min == v_max:
                        v_min, v_max = v_min - 0.1, v_max + 0.1

                stats = {
                    "mean": float(np.mean(valid_values)),
                    "max": float(np.max(valid_values)),
                    "min": float(np.min(valid_values)),
                    "std": float(np.std(valid_values)),
                    "valid_pixel_count": int(valid_pixel_count),
                    "p2": float(v_min),
                    "p98": float(v_max)
                }
            else:
                v_min, v_max = 0.0, 1.0
                stats = {
                    "mean": 0, "max": 0, "min": 0, "std": 0, "valid_pixel_count": 0,
                    "p2": 0.0, "p98": 1.0
                }

            tif_out = os.path.join(self.output_dir, f"{self.param_name}_result.tif")

            result_map_for_tif = np.copy(result_map)
            result_map_for_tif[np.isnan(result_map_for_tif)] = -9999.0

            profile.update(count=1, dtype='float32', nodata=-9999.0, compress='lzw')
            profile.pop('photometric', None)
            profile.pop('alpha', None)

            with rasterio.open(tif_out, 'w', **profile) as dst:
                dst.write(result_map_for_tif.astype('float32'), 1)
                dst.set_band_description(1, f"{self.param_name}_mapping")

            # =========================
            # ✅ 自定义Matplotlib色带（与前端保持严格一致）
            # =========================
            color_palettes = {
                'chla': ['#EDF8E9', '#BAE4B3', '#74C476', '#31A354', '#006D2C'],
                'sdd':   ['#EFF3FF', '#BDD7E7', '#6BAED6', '#3182BD', '#08519C'],
                'tp':   ['#FEEDDE', '#FDBE85', '#FD8D3C', '#E6550D', '#A63603']
            }
            # 匹配当前参数，找不到就使用默认彩虹色
            hex_colors = color_palettes.get(self.param_name.lower(), ['#0000FF', '#00FF00', '#FFFF00', '#FF7F00', '#FF0000'])
            custom_cmap = LinearSegmentedColormap.from_list(f"cmap_{self.param_name}", hex_colors)

            # 生成本地PNG
            png_out = os.path.join(self.output_dir, f"{self.param_name}_result.png")
            plt.figure(figsize=(10, 8))
            if valid_pixel_count > 0:
                img = plt.imshow(result_map, cmap=custom_cmap, vmin=v_min, vmax=v_max)
                plt.colorbar(img, label=f"{self.param_name.upper()} Value")
            else:
                plt.text(0.5, 0.5, "No Water Detected", ha='center')

            plt.title(f"Water Quality Mapping Result: {self.param_name.upper()}")
            plt.axis('off')
            plt.savefig(png_out, bbox_inches='tight', dpi=300)
            plt.close()

            csv_out = os.path.join(self.output_dir, "mapping_result.csv")
            if valid_pixel_count > 0:
                pd.DataFrame({f'{self.param_name}': valid_values}).to_csv(csv_out, index=False)
            else:
                pd.DataFrame([stats]).to_csv(csv_out, index=False)

            data.last_param_results = {
                "id": self.param_name,
                "tif": tif_out,
                "png": png_out,
                "stats": stats
            }

            # 发布图层
            publish_water_layer(
                tif_native_path=tif_out,
                layer_name=f"{self.param_name}_layer",
                param_type=self.param_name,
                vmin=v_min,
                vmax=v_max
            )

            print(f"✅ 处理完成! 有效像素: {valid_pixel_count}")
            return data
