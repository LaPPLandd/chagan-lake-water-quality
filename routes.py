# routes.py
import os
import re
import time

from flask import Blueprint, request, render_template, current_app
from werkzeug.utils import secure_filename

from core.pipeline import Pipeline
from core.data import DataPacket
from processors.unzip import UnzipProcessor
from processors.acolite import AcoliteProcessor
from processors.nc_to_tif import NcToTifProcessor
from processors.clip import ClipProcessor
from processors.mapping import MappingProcessor

api_bp = Blueprint("api", __name__)


# =========================
# 辅助函数
# =========================

# routes.py 中的 to_web_path 修改
def to_web_path(abs_path):
    """将绝对路径转换为 Web 可访问的相对路径"""
    if not abs_path: return ""
    # 统一使用正斜杠
    path = abs_path.replace("\\", "/")

    # 查找 static 关键字的位置
    if "static/" in path:
        # 获取 static/ 及其之后的所有内容，并确保前面有 /
        return "/" + path.split("static/")[-2].split("/")[-1] + "static/" + path.split("static/")[-1]

        # 更稳妥的写法：
    if "/static/" in path:
        return "/static/" + path.split("/static/")[-1]

    return path


def extract_date_from_filename(filename):
    """从 Sentinel 卫星文件名中提取日期"""
    match = re.search(r"(\d{4})(\d{2})(\d{2})T", filename)
    if match:
        year, month, day = match.groups()
        return f"{year}-{month}-{day}"
    return "未知日期"


# =========================
# 路由
# =========================

@api_bp.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@api_bp.route("/run", methods=["POST"])
def run_pipeline():
    # 1. 验证与基础数据准备
    if "file" not in request.files: return "❌ 没有上传文件"
    file = request.files["file"]
    if file.filename == "": return "❌ 文件名为空"

    filename = secure_filename(file.filename)
    image_date = extract_date_from_filename(filename)
    region = request.form.get("region", "chagan")
    model_type = request.form.get("model_type", "sentinel3")
    selected_params = request.form.getlist("params")  # 👈 获取前端勾选的列表，例如 ['chla', 'sdd']

    if not selected_params:
        return "❌ 必须至少选择一个水质参数进行反演"

    root = current_app.root_path

    # 2. 动态配置字典
    region_config = {
        "chagan": {
            "acolite": os.path.join(root, "data", "shp", "chaganbig", "chagan_big.shp"),
            "clip": os.path.join(root, "data", "shp", "chagansmall", "chagansmall.shp")
        }
        # 如果有其他地区，在此继续添加
    }

    model_config = {
        "chla": {
            "path": os.path.join(root, "models", "RF_chla_model.pkl"),
            "name": "叶绿素",
            "unit": "μg/L",
            "combinations": [
                "Rrs_620-Rrs_665",
                "Rrs_665-Rrs_682",
                "Rrs_400",
                "Rrs_412",
                "((Rrs_412 * Rrs_443) / Rrs_709)",
                "(Rrs_400 * Rrs_412)",
                "Rrs_665/Rrs_674",
                "Rrs_665/Rrs_682",
                "(Rrs_665-Rrs_674)/(Rrs_665 + Rrs_674)",
                "(Rrs_665-Rrs_682)/(Rrs_665 + Rrs_682)"
            ]
        },
        "sdd": {
            "path": os.path.join(root, "models", "RF_sdd_model.pkl"),
            "name": "透明度",
            "unit": "cm",
            # ⚠️ 注意：这里必须填入你训练透明度模型时用的真实特征公式！下面只是举例
            "combinations": [
                "(Rrs_560+Rrs_620)/Rrs_682",
                "Rrs_768-Rrs_779",
                "(Rrs_620+Rrs_665)/Rrs_674",
                "(Rrs_560 / Rrs_665)",
                "(Rrs_560-Rrs_620)/Rrs_709",
                "(Rrs_560-Rrs_665)/(Rrs_560+Rrs_665)",
                "((1/Rrs_709 + 1/Rrs_768) * Rrs_779)",
                "(Rrs_560+Rrs_620)/Rrs_674",
                "(Rrs_490-Rrs_510)/Rrs_665",
                "(Rrs_490-Rrs_510)/Rrs_682"
            ]
        },
        "tp": {
            "path": os.path.join(root, "models", "RF_tp_model.pkl"),
            "name": "总磷",
            "unit": "mg/L",
            # ⚠️ 同理，填入总磷的特征
            "combinations": [
                "Rrs_754-Rrs_768",
                "(Rrs_674-Rrs_709)/Rrs_779",
                "(Rrs_682-Rrs_709)/Rrs_768",
                "((Rrs_510 - Rrs_709) * Rrs_1016)",
                "(Rrs_490-Rrs_709)/Rrs_768",
                "(Rrs_754-Rrs_768)/(Rrs_754+Rrs_768)",
                "(Rrs_665-Rrs_709)/Rrs_768"
            ]
        }
    }

    # 提取当前地区的 SHP
    conf = region_config.get(region, region_config["chagan"])
    acolite_shp = conf["acolite"]
    clip_shp = conf["clip"]

    # 保存原始文件
    upload_dir = os.path.join(root, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    upload_path = os.path.join(upload_dir, filename)
    file.save(upload_path)

    # 3. 阶段一：运行预处理 Pipeline (大气校正 + 裁剪)
    # 这一步最耗时，所以只运行一次
    pre_processing_pipeline = Pipeline([
        UnzipProcessor(),
        AcoliteProcessor(
            acolite_exe=os.path.join(root, "tools", "acolite_GUI", "dist", "acolite", "acolite.exe"),
            settings_template=os.path.join(root, "tools", "acolite_GUI", "acolite_run_setting.txt"),
            shp_path=acolite_shp,
            output_dir=os.path.join(root, "temp", "acolite")
        ),
        NcToTifProcessor(output_dir=os.path.join(root, "temp", "tif")),
        ClipProcessor(shp_path=clip_shp, output_dir=os.path.join(root, "temp", "clip"))
    ])

    try:
        data = pre_processing_pipeline.run(DataPacket(upload_path))
    except Exception as e:
        return f"❌ 预处理阶段失败: {str(e)}"

    meta_info = {
        "region": {"chagan": "查干湖"}.get(region, "未知"),
        "date": image_date,
        "satellite": "Sentinel-3 OLCI" if model_type == "sentinel3" else "Sentinel-2 MSI"
    }

    # 4. 阶段二：循环反演选中的多个参数
    results_list = []
    report_data_items = []

    for p_id in selected_params:
        if p_id not in model_config: continue

        cfg = model_config[p_id]
        # 实例化 MappingProcessor，注意传入 param_name 以区分输出文件名
        mapping_proc = MappingProcessor(
            model_path=cfg["path"],
            output_dir=os.path.join(root, "static", "results"),
            param_name=p_id,  # 👈 确保你的 MappingProcessor 类接收这个参数
            combinations=cfg["combinations"]
        )

        try:
            # 运行反演
            data = mapping_proc.process(data)

            # 提取该参数的统计结果和路径
            # 假设你的 MappingProcessor 将结果存放在了 data.last_param_results
            res = data.last_param_results

            results_list.append({
                "id": p_id,
                "name": cfg["name"],
                "unit": cfg["unit"],
                "layer": f"water_project:{p_id}_layer",  # 与 GeoServer 发布名一致
                "stats": res["stats"],
                "tif_url": to_web_path(res["tif"]),
                "png_url": to_web_path(res["png"]),
                "ticks": [res["stats"]["min"], res["stats"]["max"]]
            })
            # 添加到报告生成数据中
            report_data_items.append({
                "name": cfg["name"],
                "unit": cfg["unit"],
                "png_path": res["png"],  # 使用绝对路径供PDF引擎读取
                "stats": res["stats"]
            })
        except Exception as e:
            print(f"⚠️ 参数 {p_id} 反演失败: {e}")

        # --- 新增：生成合并报告 ---
        report_filename = f"report_{int(time.time())}.pdf"
        report_abs_path = os.path.join(root, "static", "reports", report_filename)
        os.makedirs(os.path.dirname(report_abs_path), exist_ok=True)

        from utils.report import generate_combined_pdf  # 假设你将新逻辑写在这里
        generate_combined_pdf(report_data_items, meta_info, report_abs_path)

        report_url = to_web_path(report_abs_path)




    return render_template(
        "map.html",
        results=results_list,  # 👈 发送结果列表
        meta=meta_info,
        report_url = report_url  # 👈 传递给前端
    )
