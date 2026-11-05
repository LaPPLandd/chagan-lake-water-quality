# core/data.py

import os
from abc import ABC, abstractmethod

class DataPacket:
    """
    在整个 Pipeline 中传递的数据对象
    """

    def __init__(self, path: str):
        """
        :param path: 初始数据路径（通常是上传的 zip 或目录）
        """

        # ========================
        # 核心数据（必须有）
        # ========================
        self.path = path              # 当前处理数据路径（每一步都会被更新）

        # ========================
        # 中间数据（可选）
        # ========================
        self.nc_files = []            # Acolite 输出的 nc 文件列表
        self.tif_files = []           # 转换后的 tif 文件列表

        # ========================
        # 最终结果（Mapping输出）
        # ========================
        self.result_tif = None        # 最终反演tif
        self.result_png = None        # 可视化图片（用于网页）
        self.result_pdf = None        # PDF报告路径

        # ========================
        # 统计信息
        # ========================
        self.stats = {
            "mean": None,
            "max": None,
            "min": None
        }

        # ========================
        # 地图信息（用于前端地图显示）
        # ========================
        self.bounds = None            # [minx, miny, maxx, maxy]

    def update_path(self, new_path: str):
        """
        更新当前数据路径
        """
        if not os.path.exists(new_path):
            raise FileNotFoundError(f"路径不存在: {new_path}")
        self.path = new_path

    def __repr__(self):
        return f"<DataPacket path={self.path}>"




class BaseProcessor(ABC):
    """
    所有处理模块的基类
    """
    @abstractmethod
    def process(self, data):
        pass