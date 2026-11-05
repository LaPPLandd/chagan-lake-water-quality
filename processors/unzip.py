# processors/unzip.py

import os
from subprocess import check_call, CalledProcessError
from core.data import BaseProcessor


class UnzipProcessor(BaseProcessor):

    def __init__(self):
        # =========================
        # 项目根目录（非常关键）
        # =========================
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # 7zip路径
        self.sevenzip_exe = os.path.join(
            BASE_DIR, "tools", "7zip", "7z.exe"
        )

        # 解压输出目录
        self.unzip_dir = os.path.join(
            BASE_DIR, "temp", "unzip"
        )

    def process(self, data):

        zip_path = data.path

        # =========================
        # 基础检查
        # =========================
        if not zip_path.endswith(".zip"):
            raise Exception("❌ 输入文件不是 zip")

        if not os.path.exists(zip_path):
            raise Exception("❌ zip 文件不存在")

        if not os.path.exists(self.sevenzip_exe):
            raise Exception(f"❌ 7zip不存在: {self.sevenzip_exe}")

        os.makedirs(self.unzip_dir, exist_ok=True)

        # =========================
        # 输出目录
        # =========================
        zip_name = os.path.splitext(os.path.basename(zip_path))[0]
        output_dir = os.path.join(self.unzip_dir, zip_name)

        # 如果已存在，先删除（避免旧数据污染）
        if os.path.exists(output_dir):
            import shutil
            shutil.rmtree(output_dir)

        os.makedirs(output_dir, exist_ok=True)

        # =========================
        # 执行解压
        # =========================
        cmd = f'"{self.sevenzip_exe}" x "{zip_path}" -o"{output_dir}" -y'

        try:
            print(f"📦 解压中: {zip_path}")
            check_call(cmd, shell=True)
        except CalledProcessError as e:
            raise Exception(f"❌ 解压失败: {e}")

        # =========================
        # 自动进入 Sentinel SAFE 目录
        # =========================
        final_dir = self._find_real_data_dir(output_dir)

        print(f"✅ 解压完成: {final_dir}")

        # 更新 data
        data.path = final_dir

        return data

    # =========================
    # 查找真实数据目录（重点优化）
    # =========================
    def _find_real_data_dir(self, root_dir):
        """
        自动找到真正的影像目录（如 *.SEN3 或 SAFE）
        """

        sub_items = os.listdir(root_dir)

        # 1️⃣ 如果只有一个文件夹，直接进入
        if len(sub_items) == 1:
            sub_path = os.path.join(root_dir, sub_items[0])
            if os.path.isdir(sub_path):
                return sub_path

        # 2️⃣ 查找 Sentinel-3 目录（*.SEN3）
        for item in sub_items:
            if item.endswith(".SEN3"):
                return os.path.join(root_dir, item)

        # 3️⃣ fallback
        return root_dir