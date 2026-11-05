# utils/report.py

from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Spacer
from reportlab.lib.styles import getSampleStyleSheet


def generate_pdf(output_path, image_path, stats):
    doc = SimpleDocTemplate(output_path)
    styles = getSampleStyleSheet()

    content = []

    content.append(Paragraph("Water Quality Report", styles["Title"]))
    content.append(Spacer(1, 20))

    content.append(Image(image_path, width=400, height=300))
    content.append(Spacer(1, 20))

    content.append(Paragraph(f"Mean: {stats['mean']:.3f}", styles["Normal"]))
    content.append(Paragraph(f"Max: {stats['max']:.3f}", styles["Normal"]))
    content.append(Paragraph(f"Min: {stats['min']:.3f}", styles["Normal"]))

    doc.build(content)