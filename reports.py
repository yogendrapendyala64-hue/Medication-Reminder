"""Weekly adherence report: data for the HTML view and a downloadable PDF."""
import os
import re
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

import models

REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
BRAND = colors.HexColor("#2a8267")


def build_report(db, patient_id):
    patient = models.get_patient(db, patient_id)
    week = models.week_stats(db, patient_id)
    return {
        "patient": patient,
        "week": week,
        "meds": models.list_prescriptions(db, patient_id, active_only=True),
        "generated": date.today().strftime("%B %d, %Y").replace(" 0", " "),
        "activity": [
            f"{r['log_date']} • {r['med']} • {'Taken' if r['status'] == 'taken' else 'Missed'}"
            for r in week["logs"]
        ],
    }


def report_filename(patient):
    slug = re.sub(r"[^a-z0-9]+", "-", patient["name"].lower()).strip("-") or "patient"
    return f"{slug}-weekly-report.pdf"


def generate_pdf(data, folder=REPORTS_DIR):
    """Write the report to reports/ and return the file path."""
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, report_filename(data["patient"]))
    styles = getSampleStyleSheet()
    title = ParagraphStyle("t", parent=styles["Title"], textColor=BRAND, alignment=0, fontSize=24, spaceAfter=2)
    sub = ParagraphStyle("s", parent=styles["Normal"], textColor=colors.HexColor("#555555"), fontSize=10)
    h = ParagraphStyle("h", parent=styles["Heading2"], spaceBefore=16, spaceAfter=6, fontSize=13)
    body = ParagraphStyle("b", parent=styles["Normal"], fontSize=10.5, leading=15)
    note = ParagraphStyle("n", parent=body, leftIndent=14, textColor=colors.HexColor("#555555"))

    p, w = data["patient"], data["week"]
    esc = lambda s: str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    story = [
        Paragraph("MediPulse", title),
        Paragraph("Weekly medication adherence report", sub),
        Spacer(1, 18),
        Paragraph(esc(p["name"]), ParagraphStyle("p", parent=styles["Heading1"], fontSize=18)),
        Paragraph(f"Generated {data['generated']} &bull; {esc(p['condition'])}", sub),
        Paragraph("Weekly overview", h),
        Paragraph(f"Adherence: <b>{w['pct']}%</b> &nbsp;&nbsp; Taken: <b>{w['taken']}</b> &nbsp;&nbsp; Missed: <b>{w['missed']}</b>", body),
        Paragraph("Active medications", h),
    ]
    if data["meds"]:
        for m in data["meds"]:
            story.append(Paragraph(f"{esc(m['name'])} &mdash; {esc(m['dosage'])} &mdash; {esc(m['frequency'])} at {esc(m['reminder_time'])}", body))
            if m["instructions"]:
                story.append(Paragraph(esc(m["instructions"]), note))
    else:
        story.append(Paragraph("No active medications.", body))
    story.append(Paragraph("Recent dose activity", h))
    if data["activity"]:
        for line in data["activity"]:
            story.append(Paragraph(esc(line), body))
    else:
        story.append(Paragraph("No doses were logged this week.", body))

    SimpleDocTemplate(path, pagesize=letter, leftMargin=inch, rightMargin=inch, topMargin=inch,
                      bottomMargin=inch, title=f"Weekly report - {p['name']}", author="MediPulse").build(story)
    return path
