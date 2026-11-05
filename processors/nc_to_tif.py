# processors/nc_to_tif.py

from core.data import BaseProcessor
import xarray as xr
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from pyresample import geometry, kd_tree
import os


class NcToTifProcessor(BaseProcessor):

    def __init__(self, output_dir, rrs_columns=None, resolution=0.003):
        """
        :param output_dir: 输出目录
        :param rrs_columns: 波段列表
        :param resolution: 重采样分辨率（度）
        """
        self.output_dir = output_dir
        self.resolution = resolution

        self.rrs_columns = rrs_columns or [
            "Rrs_400", "Rrs_412", "Rrs_443", "Rrs_490", "Rrs_510",
            "Rrs_560", "Rrs_620", "Rrs_665", "Rrs_674", "Rrs_682",
            "Rrs_709", "Rrs_754", "Rrs_768", "Rrs_779",
            "Rrs_865", "Rrs_884", "Rrs_1016"
        ]

    def process(self, data):

        nc_path = self.find_nc(data.path)
        print(f"📦 读取NC文件: {nc_path}")

        ds = xr.open_dataset(nc_path)

        # =========================
        # 1️⃣ 获取经纬度（不规则）
        # =========================
        lat = ds["lat"].values
        lon = ds["lon"].values

        # =========================
        # 2️⃣ 构建 Swath（关键）
        # =========================
        src_def = geometry.SwathDefinition(
            lons=lon,
            lats=lat
        )

        # =========================
        # 3️⃣ 构建目标规则网格
        # =========================
        min_lon, max_lon = np.nanmin(lon), np.nanmax(lon)
        min_lat, max_lat = np.nanmin(lat), np.nanmax(lat)

        res = self.resolution

        target_lons = np.arange(min_lon, max_lon, res)
        target_lats = np.arange(max_lat, min_lat, -res)

        grid_lon, grid_lat = np.meshgrid(target_lons, target_lats)

        tgt_def = geometry.GridDefinition(
            lons=grid_lon,
            lats=grid_lat
        )

        height, width = grid_lat.shape

        # =========================
        # 4️⃣ transform（现在是正确的）
        # =========================
        transform = from_bounds(
            min_lon, min_lat, max_lon, max_lat,
            width, height
        )

        # =========================
        # 5️⃣ 检查波段
        # =========================
        available = [b for b in self.rrs_columns if b in ds]

        if len(available) == 0:
            raise Exception(f"❌ 没有找到Rrs波段: {list(ds.data_vars)}")

        print(f"✅ 使用波段: {available}")

        # =========================
        # 6️⃣ 输出路径
        # =========================
        os.makedirs(self.output_dir, exist_ok=True)
        output_path = os.path.join(self.output_dir, "converted.tif")

        # =========================
        # 7️⃣ 写入 GeoTIFF
        # =========================
        with rasterio.open(
            output_path,
            "w",
            driver="GTiff",
            height=height,
            width=width,
            count=len(available),
            dtype="float32",
            crs="EPSG:4326",
            transform=transform,
            nodata=np.nan,
            compress="lzw"
        ) as dst:

            for i, var in enumerate(available, start=1):

                print(f"▶ 重采样 {var} ({i}/{len(available)})")

                data_arr = ds[var].values
                data_arr = np.where(np.isfinite(data_arr), data_arr, np.nan)

                resampled = kd_tree.resample_nearest(
                    src_def,
                    data_arr,
                    tgt_def,
                    radius_of_influence=500,
                    fill_value=np.nan
                )

                dst.write(resampled.astype("float32"), i)
                dst.set_band_description(i, var)

        print(f"✅ TIF生成（重采样完成）: {output_path}")

        # =========================
        # 8️⃣ 传递给后续模块
        # =========================
        data.path = output_path
        data.band_names = available   # 👉 Mapping用

        return data

    def find_nc(self, folder):
        for root, _, files in os.walk(folder):
            for f in files:
                if f.endswith(".nc"):
                    return os.path.join(root, f)
        raise Exception("❌ 未找到NC文件")