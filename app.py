import os
from flask import Flask, render_template, send_from_directory ,request, Response
import requests
from routes import api_bp  # 确保你的 routes.py 中定义了 api_bp
import logging


app = Flask(__name__)
# 定义一个过滤器
class NoProxyFilter(logging.Filter):
    def filter(self, record):
        # 如果日志消息里包含 'geoserver_proxy'，就返回 False (不打印)
        return 'geoserver_proxy' not in record.getMessage()

# 将过滤器应用到 Werkzeug 日志
log = logging.getLogger('werkzeug')
log.addFilter(NoProxyFilter())

# ==============================
# 1. 配置与路径 (请根据你的实际磁盘路径核对)
# ==============================
# 存放卫星底图的 D 盘路径
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKGROUND_DIR = os.path.join(PROJECT_DIR, "data", "background")

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULT_FOLDER'] = 'static/results'
# 限制上传大小为 1GB
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024

GEOSERVER_REPORT_DIR = os.environ.get(
    'GEOSERVER_REPORT_DIR',
    os.path.join(PROJECT_DIR, 'tools', 'geoserver', 'data_dir', 'reports')
)
if not os.path.exists(GEOSERVER_REPORT_DIR):
    os.makedirs(GEOSERVER_REPORT_DIR, exist_ok=True)
# ==============================
# 2. 目录初始化 (启动时自动创建)
# ==============================
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)
if not os.path.exists(BACKGROUND_DIR):
    os.makedirs(BACKGROUND_DIR, exist_ok=True)

# ==============================
# 3. 特殊资源服务路由
# ==============================

@app.route('/background_data/<path:filename>')
def serve_background(filename):
    """
    专门用于读取 D 盘非项目目录下的底图文件
    前端调用示例: /background_data/background_rgb.tif
    """
    return send_from_directory(BACKGROUND_DIR, filename)

@app.route('/results_data/<path:filename>')
def serve_results(filename):
    """
    提供结果目录文件的访问
    """
    return send_from_directory(app.config['RESULT_FOLDER'], filename)

@app.route('/download_report/<path:filename>')
def serve_report(filename):
    """
    专门用于下载保存在 GeoServer 目录下的 PDF 报告
    """
    # as_attachment=True 会强制浏览器弹出下载框，而不是直接打开
    return send_from_directory(GEOSERVER_REPORT_DIR, filename, as_attachment=True)
# ==============================
# 4. 蓝图注册 (核心业务逻辑)
# ==============================
# 注册后，routes.py 中的 @api_bp.route('/') 将成为首页
app.register_blueprint(api_bp)

# ==============================
# 5. 错误处理 (可选，防止白屏)
# ==============================
# @app.errorhandler(500)
# def internal_error(error):
#     return "🚀 服务器内部错误：请检查 Python 控制台的报错日志 (Jinja2 渲染或路径问题)", 500

@app.errorhandler(404)
def not_found_error(error):
    return "🔍 页面未找到：请确认你访问的地址是否正确", 404


@app.route('/geoserver_proxy')
def geoserver_proxy():
    # GeoServer 的原始 WMS 地址
    base_url = "http://localhost:8080/geoserver/water_project/wms"

    # 转发前端传来的所有 GetFeatureInfo 参数
    resp = requests.get(base_url, params=request.args)

    # 将响应原封不动返回给前端，包括 Content-Type
    return Response(resp.content, content_type=resp.headers['content-type'])

# ==============================
# 6. 启动服务
# ==============================
if __name__ == "__main__":
    # 使用 debug=True 可以实时看到代码修改后的重启
    # threaded=True 允许同时处理地图瓦片和页面请求
    print("--- Flask 服务启动中 ---")
    print(f"首页地址: http://127.0.0.1:5012")
    app.run(host='0.0.0.0', port=5012, debug=True, threaded=True)
