# processors/acolite.py

from core.data import BaseProcessor
import os
from subprocess import check_call, CalledProcessError


class AcoliteProcessor(BaseProcessor):
    """
    Acolite大气校正处理模块（工程版）
    """

    def __init__(self, acolite_exe, settings_template, shp_path, output_dir):
        """
        :param acolite_exe: acolite.exe路径（项目内）
        :param settings_template: 设置模板
        :param shp_path: 裁剪矢量
        :param output_dir: 输出目录
        """
        self.acolite_exe = os.path.abspath(acolite_exe)
        self.settings_template = os.path.abspath(settings_template)
        self.shp_path = os.path.abspath(shp_path)
        self.output_dir = os.path.abspath(output_dir)

        # 读取模板
        if not os.path.exists(self.settings_template):
            raise Exception("Acolite settings模板不存在")

        with open(self.settings_template, 'r', encoding='utf-8') as f:
            self.template_lines = f.read().split('\n')

    def process(self, data):
        input_dir = os.path.abspath(data.path)

        if not os.path.exists(input_dir):
            raise Exception(f"输入路径不存在: {input_dir}")

        print(f"🌍 Acolite输入: {input_dir}")

        # 创建输出目录
        name = os.path.basename(input_dir.rstrip("\\/"))
        output_dir = os.path.join(self.output_dir, name)

        os.makedirs(output_dir, exist_ok=True)

        # =========================
        # 生成 settings 文件
        # =========================
        setting_lines = self.template_lines.copy()

        # ⚠️ 注意：这里依赖你模板格式（推荐后期优化成key查找）
        setting_lines[2] = f'inputfile={input_dir}'
        setting_lines[3] = f'output={output_dir}'
        setting_lines[4] = f'polygon={self.shp_path}'

        setting_file = os.path.join(output_dir, "acolite_run_setting.txt")

        with open(setting_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(setting_lines) + '\n')

        # =========================
        # 执行 Acolite
        # =========================
        cmd = f'"{self.acolite_exe}" --cli --settings="{setting_file}"'

        print(f"🚀 执行Acolite...\n{cmd}")

        try:
            check_call(cmd, shell=True)
        except CalledProcessError as e:
            raise Exception(f"❌ Acolite执行失败: {e}")

        print(f"✅ Acolite完成: {output_dir}")

        # 更新数据流
        data.path = output_dir
        return data