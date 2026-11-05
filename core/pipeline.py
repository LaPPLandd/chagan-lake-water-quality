# core/pipeline.py

import time


class Pipeline:
    """
    处理流程控制器（核心调度）
    """

    def __init__(self, steps=None):
        """
        :param steps: Processor 实例列表
        """
        self.steps = steps or []

        if not isinstance(self.steps, list):
            raise ValueError("steps 必须是 list")

    # =====================================
    # 主执行函数
    # =====================================
    def run(self, data):
        """
        执行整个处理流程

        :param data: DataPacket
        :return: DataPacket
        """

        if data is None:
            raise ValueError("data 不能为空")

        if not hasattr(data, "path"):
            raise ValueError("data 必须包含 path 属性")

        print("\n" + "=" * 60)
        print("🚀 Pipeline 开始执行")
        print("=" * 60)

        total_start = time.time()

        # ========================
        # 逐个执行 Processor
        # ========================
        for idx, step in enumerate(self.steps):

            step_name = step.__class__.__name__

            print(f"\n➡️ Step {idx + 1}/{len(self.steps)}: {step_name}")

            start_time = time.time()

            try:
                # 核心执行
                data = step.process(data)

                if data is None:
                    raise RuntimeError(f"{step_name} 返回 None")

                if not hasattr(data, "path"):
                    raise RuntimeError(f"{step_name} 未正确返回 DataPacket")

                elapsed = time.time() - start_time

                print(f"✅ {step_name} 完成")
                print(f"📁 当前路径: {data.path}")
                print(f"⏱️ 耗时: {elapsed:.2f} 秒")

            except Exception as e:
                print(f"\n❌ {step_name} 执行失败")
                print(f"错误信息: {str(e)}")
                raise e  # 交给 Flask 处理

        total_time = time.time() - total_start

        print("\n" + "=" * 60)
        print("🎉 Pipeline 执行完成")
        print(f"总耗时: {total_time:.2f} 秒")
        print("=" * 60)

        return data

    # =====================================
    # 扩展功能（工程推荐）
    # =====================================

    def add_step(self, step):
        self.steps.append(step)

    def insert_step(self, index, step):
        self.steps.insert(index, step)

    def clear(self):
        self.steps = []

    def list_steps(self):
        return [step.__class__.__name__ for step in self.steps]