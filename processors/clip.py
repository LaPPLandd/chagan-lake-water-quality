# processors/clip.py

import os
import rasterio
import geopandas as gpd
from rasterio.mask import mask
from core.data import BaseProcessor
import numpy as np


class ClipProcessor(BaseProcessor):

    def __init__(self, shp_path, output_dir):
        self.shp_path = shp_path
        self.output_dir = output_dir

    def process(self, data):

        tif_in = data.path
        os.makedirs(self.output_dir, exist_ok=True)

        tif_out = os.path.join(self.output_dir, "clipped.tif")

        print(f"✂️ 开始裁剪流程: {tif_in}")

        # =========================
        # 1️⃣ 检查文件
        # =========================
        if not os.path.exists(tif_in):
            raise Exception(f"❌ TIF不存在: {tif_in}")

        if not os.path.exists(self.shp_path):
            raise Exception(f"❌ SHP不存在: {self.shp_path}")

        # =========================
        # 2️⃣ 读取 SHP
        # =========================
        gdf = gpd.read_file(self.shp_path)

        if gdf.empty:
            raise Exception("❌ SHP为空")

        # 只保留 Polygon
        gdf = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])]

        if gdf.empty:
            raise Exception("❌ SHP中没有Polygon")

        # 修复几何（关键）
        gdf["geometry"] = gdf["geometry"].buffer(0)

        # =========================
        # 3️⃣ 打开影像
        # =========================
        with rasterio.open(tif_in) as src:

            print("📍 TIF CRS:", src.crs)
            print("📍 SHP CRS:", gdf.crs)

            # -------------------------
            # CRS 对齐（关键）
            # -------------------------
            if gdf.crs != src.crs:
                print("🔄 坐标系不一致 → 自动重投影")
                gdf = gdf.to_crs(src.crs)

            # -------------------------
            # 🔥 强制检查范围（防止错位）
            # -------------------------
            tif_bounds = src.bounds
            shp_bounds = gdf.total_bounds

            print("🧭 TIF范围:", tif_bounds)
            print("🧭 SHP范围:", shp_bounds)

            # 如果完全不相交 → 直接报错（避免生成空图）
            if not self._bounds_intersect(tif_bounds, shp_bounds):
                raise Exception("❌ SHP与TIF完全不重叠（坐标可能错误）")

            # -------------------------
            # 转 GeoJSON（关键）
            # -------------------------
            geoms = [
                geom.__geo_interface__
                for geom in gdf.geometry
                if geom is not None
            ]

            # -------------------------
            # 执行裁剪
            # -------------------------
            out_image, out_transform = mask(
                src,
                geoms,
                crop=True,
                filled=True,
                nodata=np.nan   # 🔥 改为 NaN（更适合后续反演）
            )

            out_meta = src.meta.copy()
            original_descriptions = src.descriptions

        # =========================
        # 4️⃣ 更新元数据
        # =========================
        out_meta.update({
            "driver": "GTiff",
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform,
            "nodata": np.nan,
            "compress": "lzw"
        })

        # =========================
        # 5️⃣ 写入结果
        # =========================
        with rasterio.open(tif_out, "w", **out_meta) as dst:
            dst.write(out_image)

            # 恢复波段名（关键）
            if original_descriptions:
                dst.descriptions = original_descriptions

        print(f"✅ 裁剪完成: {tif_out}")

        data.path = tif_out
        return data

    # =========================
    # 判断是否相交
    # =========================
    def _bounds_intersect(self, b1, b2):
        return not (
            b1.right < b2[0] or
            b1.left > b2[2] or
            b1.top < b2[1] or
            b1.bottom > b2[3]
        )