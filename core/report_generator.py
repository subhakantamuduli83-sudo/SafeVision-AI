import os
import csv
import io
from datetime import datetime
import sqlite3
from core.database import DB_PATH

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False


def generate_pdf_report(output_path: str = "Safety_Compliance_Audit_Report.pdf") -> str:
    """Generates an executive Safety Compliance Audit PDF report."""
    if not REPORTLAB_AVAILABLE:
        # Fallback to simple HTML or text report
        with open(output_path.replace(".pdf", ".html"), "w", encoding="utf-8") as f:
            f.write("<h1>Safety Compliance Audit Report</h1><p>Reportlab not installed.</p>")
        return output_path.replace(".pdf", ".html")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=22,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=15
    )
    heading2_style = ParagraphStyle(
        'H2Style',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=12,
        spaceAfter=8
    )

    elements = []

    # Title & Header
    elements.append(Paragraph("INDUSTRIAL SAFETY & PPE COMPLIANCE AUDIT REPORT", title_style))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | STPI & EmTek Hackathon", subtitle_style))
    elements.append(Spacer(1, 10))

    # Fetch Database Summary
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM incidents ORDER BY id DESC LIMIT 50")
    incidents = cur.fetchall()

    # Fetch latest weather reading
    cur.execute("SELECT * FROM weather_logs ORDER BY id DESC LIMIT 1")
    latest_weather = cur.fetchone()

    total_incidents = len(incidents)
    helmet_count = sum(1 for inc in incidents if "Helmet" in inc["incident_type"])
    vest_count = sum(1 for inc in incidents if "Vest" in inc["incident_type"])
    fire_count = sum(1 for inc in incidents if "Fire" in inc["incident_type"])
    thermal_count = sum(1 for inc in incidents if "Thermal" in inc["incident_type"] or "Heat" in inc["incident_type"])
    conn.close()

    weather_desc = f"{latest_weather['temperature']}°C (Heat Index: {latest_weather['heat_index']}°C, {latest_weather['humidity']}% RH)" if latest_weather else "N/A"
    weather_risk = latest_weather['risk_level'] if latest_weather else "Normal"

    # Summary Metrics Table
    summary_data = [
        ["Metric", "Value", "Status"],
        ["Total Safety Incidents Logged", str(total_incidents), "Critical" if total_incidents > 10 else "Normal"],
        ["Hardhat / Helmet Violations", str(helmet_count), "High Priority" if helmet_count > 0 else "Clear"],
        ["High-Vis Vest Violations", str(vest_count), "High Priority" if vest_count > 0 else "Clear"],
        ["Fire & Smoke Emergency Triggers", str(fire_count), "ALERT" if fire_count > 0 else "Safe"],
        ["Thermal / Heat Stress Hazards", str(thermal_count), "ALERT" if thermal_count > 0 else "Safe"],
        ["Current Environmental Climate", weather_desc, weather_risk],
    ]

    summary_table = Table(summary_data, colWidths=[240, 150, 110])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#F8FAFC'), colors.white]),
    ]))

    elements.append(Paragraph("Executive Compliance Summary", heading2_style))
    elements.append(summary_table)
    elements.append(Spacer(1, 15))

    # Detailed Incident Logs
    elements.append(Paragraph("Detailed Incident Log (Recent Events)", heading2_style))

    log_data = [["ID", "Timestamp", "Zone", "Incident Type", "Severity"]]
    for inc in incidents[:15]:
        log_data.append([
            str(inc["id"]),
            inc["timestamp"],
            inc["zone"][:20],
            inc["incident_type"][:25],
            inc["severity"]
        ])

    if len(log_data) == 1:
        log_data.append(["-", "No incidents recorded", "-", "-", "-"])

    log_table = Table(log_data, colWidths=[30, 120, 120, 150, 80])
    log_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#334155')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
    ]))

    elements.append(log_table)

    # Build PDF
    doc.build(elements)
    return output_path


def generate_csv_report() -> str:
    """Exports all incident logs to a CSV string."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM incidents ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Timestamp", "Zone", "Incident Type", "Severity", "Details", "Snapshot Path", "Acknowledged"])
    for row in rows:
        writer.writerow([row["id"], row["timestamp"], row["zone"], row["incident_type"], row["severity"], row["details"], row["snapshot_path"], row["acknowledged"]])

    return output.getvalue()

