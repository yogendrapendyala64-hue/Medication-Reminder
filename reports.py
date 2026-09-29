from datetime import datetime, timedelta
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)

from database import query


def get_weekly_data(patient_id):

    start = datetime.now()

    start = start.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    start = start - timedelta(days=6)

    end = start + timedelta(days=7)

    patient = query(
        """
        SELECT
            id,
            full_name,
            email
        FROM users
        WHERE id = %s
        AND role = 'patient'
        """,
        (patient_id,),
        fetchall=False
    )

    rows = query(
        """
        SELECT
            p.medicine_name,
            p.dose,
            s.scheduled_at,
            s.status

        FROM dose_slots s

        INNER JOIN prescriptions p
            ON p.id = s.prescription_id

        WHERE p.patient_id = %s

        AND s.scheduled_at >= %s
        AND s.scheduled_at < %s

        ORDER BY
            p.medicine_name,
            s.scheduled_at
        """,
        (
            patient_id,
            start,
            end
        )
    )

    return patient, start, end, rows


def build_weekly_pdf(patient_id):

    patient, start, end, rows = get_weekly_data(
        patient_id
    )

    if not patient:
        return None

    summary = {}

    for row in rows:

        medicine = row["medicine_name"]

        if medicine not in summary:

            summary[medicine] = {
                "dose": row["dose"],
                "scheduled": 0,
                "taken": 0,
                "missed": 0,
                "pending": 0
            }

        summary[medicine]["scheduled"] += 1

        if row["status"] == "taken":

            summary[medicine]["taken"] += 1

        elif row["status"] == "missed":

            summary[medicine]["missed"] += 1

        else:

            summary[medicine]["pending"] += 1

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    story = []

    story.append(
        Paragraph(
            "Medication Reminder - Weekly Report",
            styles["Title"]
        )
    )

    story.append(
        Spacer(1, 10)
    )

    story.append(
        Paragraph(
            f"<b>Patient:</b> {patient['full_name']}",
            styles["Normal"]
        )
    )

    story.append(
        Paragraph(
            f"<b>Email:</b> {patient['email']}",
            styles["Normal"]
        )
    )

    story.append(
        Paragraph(
            f"<b>Period:</b> "
            f"{start.strftime('%d %b %Y')} - "
            f"{(end - timedelta(days=1)).strftime('%d %b %Y')}",
            styles["Normal"]
        )
    )

    story.append(
        Spacer(1, 18)
    )

    table_data = [
        [
            "Medicine",
            "Dose",
            "Scheduled",
            "Taken",
            "Missed",
            "Pending",
            "Adherence"
        ]
    ]

    for medicine, data in summary.items():

        adherence = (
            data["taken"]
            / data["scheduled"]
            * 100
            if data["scheduled"]
            else 0
        )

        table_data.append(
            [
                medicine,
                data["dose"],
                data["scheduled"],
                data["taken"],
                data["missed"],
                data["pending"],
                f"{adherence:.1f}%"
            ]
        )

    if len(table_data) == 1:

        table_data.append(
            [
                "No medication data",
                "-",
                "0",
                "0",
                "0",
                "0",
                "0%"
            ]
        )

    table = Table(
        table_data,
        repeatRows=1,
        colWidths=[
            85,
            55,
            55,
            45,
            45,
            50,
            55
        ]
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#17352d")
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold"
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#d8ddd8")
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    8
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE"
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    7
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7
                )
            ]
        )
    )

    story.append(table)

    story.append(
        Spacer(1, 20)
    )

    story.append(
        Paragraph(
            "This report contains medication schedules "
            "and the recorded taken/missed status.",
            styles["BodyText"]
        )
    )

    document.build(story)

    buffer.seek(0)

    return buffer