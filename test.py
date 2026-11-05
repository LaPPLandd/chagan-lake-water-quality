import rasterio
import numpy as np

import os

raster_path = os.environ.get(
    "TEST_RASTER_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools", "geoserver", "data_dir", "rasters", "sdd_result.tif")
)

with rasterio.open(raster_path) as src:
    print(f"数据类型 (dtype): {src.dtypes[0]}")
    # 读取一个小块查看具体数值是否有小数点
    sample = src.read(1)[50:60, 50:60]
    print("样本数值内容:")
    print(sample)

    data = src.read(1)
    # 过滤掉无效值后，查看有多少个不同的数值
    unique_values = np.unique(data[data > -5000])
    print(f"有效数据中唯一值的个数: {len(unique_values)}")
