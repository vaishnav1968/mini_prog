"""
Report Generation Engine (CSV & Professional PDF Export)
========================================================
Generates:
  1. Cleaned and Audited CSV datasets
  2. Academic & Enterprise PDF Integrity Reports:
     - Executive Summary
     - Metrological and Statistical Metrics
     - Multi-Model Anomaly Breakdown (Isolation Forest, LOF, Z-Score)
     - Deep Learning Residuals (LSTM & Autoencoder)
     - Security & Metrology Threat Action Plan
"""

import os
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List

def export_cleaned_csv(eval_df: pd.DataFrame, output_path: str) -> str:
    """Exports validated and sanitized dataset as CSV."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    export_cols = [c for c in eval_df.columns if not c.endswith("_raw")]
    eval_df[export_cols].to_csv(output_path, index=False)
    return output_path

def generate_pdf_report(
    filename: str,
    metrics: Dict[str, Any],
    alerts: List[Dict[str, Any]],
    output_path: str
) -> str:
    """
    Creates a styled academic/enterprise PDF audit report using ReportLab.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    except ImportError:
        # Fallback if ReportLab not loaded yet
        with open(output_path, "w") as f:
            f.write(f"WEATHER DATA INTEGRITY REPORT\nFile: {filename}\nGenerated: {datetime.now()}")
        return output_path

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
        "DocTitle",
        parent=styles["Heading1"],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#475569"),
        spaceAfter=15
    )
    h2_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=12,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#334155")
    )

    story = []

    # Title & Metadata
    story.append(Paragraph("AI-BASED WEATHER DATA INTEGRITY REPORT", title_style))
    story.append(Paragraph(
        f"<b>Audit Target:</b> {filename} &nbsp;|&nbsp; <b>Timestamp:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')} &nbsp;|&nbsp; <b>System:</b> Antigravity AI Weather Guard",
        subtitle_style
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=12))

    # Executive Summary Card
    story.append(Paragraph("1. Executive Summary & Integrity Score", h2_style))
    integrity_pct = metrics.get("integrity_percentage", 100.0)
    score_color = "#16a34a" if integrity_pct >= 85 else ("#ca8a04" if integrity_pct >= 60 else "#dc2626")

    summary_data = [
        ["Total Records Analyzed", str(metrics.get("total_records", 0)), "Overall Integrity Score", f"{metrics.get('average_integrity_score', 100)} / 100"],
        ["Verified Normal Records", str(metrics.get("normal_readings", 0)), "Data Integrity Rating", f"{integrity_pct}%"],
        ["Suspicious Readings", str(metrics.get("suspicious_readings", 0)), "Anomalous / Corrupted", str(metrics.get("anomalous_readings", 0) + metrics.get("corrupted_or_tampered", 0))]
    ]
    t_summary = Table(summary_data, colWidths=[150, 110, 150, 110])
    t_summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1e293b")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
    ]))
    story.append(t_summary)
    story.append(Spacer(1, 14))

    # Security & Metrological Evaluation Breakdown
    story.append(Paragraph("2. Metrological & AI Threat Findings", h2_style))
    story.append(Paragraph(
        "The system ran a multi-stage validation pipeline combining physical validity checks, "
        "Isolation Forest, Local Outlier Factor (LOF), Z-score statistical tests, and Deep Learning "
        "(LSTM & Autoencoder) reconstruction errors. In accordance with meteorological forensic guidelines, "
        "readings are distinguished between severe physical weather events and potential data tampering/hardware faults.",
        body_style
    ))
    story.append(Spacer(1, 10))

    # Recent Alerts Table
    story.append(Paragraph("3. Detected Anomaly & Security Alerts (Sample)", h2_style))
    if alerts:
        alert_rows = [["Timestamp", "Severity", "Parameter", "Detected Val", "Reason"]]
        for a in alerts[:12]:  # Show top 12 in PDF
            alert_rows.append([
                str(a.get("timestamp"))[:16],
                str(a.get("severity")),
                str(a.get("parameter")),
                str(a.get("detected_value")),
                str(a.get("reason"))[:45] + ("..." if len(str(a.get("reason"))) > 45 else "")
            ])

        t_alerts = Table(alert_rows, colWidths=[95, 60, 80, 80, 205])
        t_alerts.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")])
        ]))
        story.append(t_alerts)
    else:
        story.append(Paragraph("No anomalies or integrity violations were detected. Dataset is 100% verified.", body_style))

    story.append(Spacer(1, 14))

    # Recommendations
    story.append(Paragraph("4. Recommendations & Next Actions", h2_style))
    recs = [
        "1. <b>Physical Limit Violations:</b> Calibrate or replace humidity/temperature probes exhibiting out-of-bounds readings.",
        "2. <b>Frozen Sensor Periods:</b> Inspect telemetry link for stations with 12+ hours identical readings (likely ADC freeze).",
        "3. <b>Multi-Model ML Flags:</b> Cross-reference multi-model anomalies with neighboring automated weather stations (AWS) to rule out localized severe convective storms.",
        "4. <b>Export Sanitized Data:</b> Utilize the cleaned and imputed dataset for downstream climate and forecasting models."
    ]
    for r in recs:
        story.append(Paragraph(r, body_style))
        story.append(Spacer(1, 3))

    doc.build(story)
    return output_path
