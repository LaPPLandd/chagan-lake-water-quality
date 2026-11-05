# utils/report.py
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os


# ================= 核心修复：注册中文字体 =================
def register_chinese_font():
    """
    注册系统自带的中文字体。优先尝试微软雅黑，其次是宋体。
    """
    # 常见的 Windows 系统字体路径
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑
        "C:/Windows/Fonts/simsun.ttc",  # 宋体
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",  # Linux 常用路径
    ]

    font_registered = False
    for path in font_paths:
        if os.path.exists(path):
            try:
                # 注册字体，命名为 'ChineseFont'
                pdfmetrics.registerFont(TTFont('ChineseFont', path))
                font_registered = True
                print(f"✅ 已成功注册中文字体: {path}")
                break
            except Exception as e:
                print(f"⚠️ 字体 {path} 注册失败: {e}")

    if not font_registered:
        print("❌ 警告：未找到支持中文的系统字体，PDF 中文可能仍会乱码！")
    return "ChineseFont" if font_registered else "Helvetica"


# 获取已注册的字体名称
CHINESE_FONT = register_chinese_font()


def generate_combined_pdf(data_items, meta, output_path):
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    for item in data_items:
        # --- 每一页的标题 ---
        # 使用注册好的中文字体
        c.setFont(CHINESE_FONT, 16)
        c.drawString(50, height - 50, f"水质分析报告 - {item['name']}")

        c.setFont(CHINESE_FONT, 10)
        c.drawString(50, height - 70,
                     f"监测地区: {meta['region']} | 时间: {meta['date']} | 卫星: {meta['satellite']}")
        c.line(50, height - 75, width - 50, height - 75)

        # --- 上半部分：反演图 ---
        if os.path.exists(item['png_path']):
            img_w, img_h = 450, 350
            c.drawImage(item['png_path'], (width - img_w) / 2, height - 450, width=img_w, height=img_h)

        # --- 下半部分：统计表格 ---
        # 如果你的表格里有中文（比如指标名称），这里也需要修改
        table_data = [
            ['统计指标', '数值', '单位'],
            ['最大值', f"{item['stats']['max']:.2f}", item['unit']],
            ['平均值', f"{item['stats']['mean']:.2f}", item['unit']],
            ['最小值', f"{item['stats']['min']:.2f}", item['unit']],
            ['标准差', f"{item['stats']['std']:.2f}", item['unit']],
            ['有效像素数量', f"{item['stats']['valid_pixel_count']}", 'px']
        ]

        t = Table(table_data, colWidths=[150, 100, 100])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            # 💡 关键：表格样式也必须指定中文字体
            ('FONTNAME', (0, 0), (-1, -1), CHINESE_FONT),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        t.wrapOn(c, width, height)
        t.drawOn(c, 100, 150)

        # 页码
        c.setFont(CHINESE_FONT, 8)
        c.drawRightString(width - 50, 30, f"第 {data_items.index(item) + 1} 页，共 {len(data_items)} 页")

        c.showPage()

    c.save()