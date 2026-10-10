"""Finds doses that are due and sends the reminder (email if SMTP is set up, otherwise the log)."""
import logging
import os
import smtplib
from datetime import datetime
from email.message import EmailMessage

from database import connect

log = logging.getLogger("medipulse.reminders")


def deliver(to_addr, subject, body):
    """Send one email. Returns the channel used: 'email' or 'log'."""
    host = os.environ.get("SMTP_HOST", "").strip()
    if not host:
        log.info("[reminder] to=%s | %s | %s", to_addr, subject, body.replace("\n", " "))
        return "log"
    msg = EmailMessage()
    msg["From"] = os.environ.get("MAIL_FROM", "MediPulse <reminders@medipulse.local>")
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", "587")), timeout=15) as smtp:
        smtp.starttls()
        user = os.environ.get("SMTP_USER", "")
        if user:
            smtp.login(user, os.environ.get("SMTP_PASSWORD", ""))
        smtp.send_message(msg)
    return "email"


def send_due_reminders(db_path, now=None):
    """Remind every patient whose dose time is now and who has not logged today's dose. Returns the count sent."""
    now = now or datetime.now()
    today, hhmm = now.date().isoformat(), now.strftime("%H:%M")
    db = connect(db_path)
    sent = 0
    try:
        rows = db.execute(
            "SELECT rx.id, rx.name, rx.dosage, rx.instructions, rx.end_date, p.name AS patient, p.email"
            " FROM prescriptions rx JOIN patients p ON p.id = rx.patient_id"
            " WHERE rx.reminder_time = ? AND rx.start_date <= ? AND (rx.end_date = '' OR rx.end_date >= ?)"
            " AND NOT EXISTS (SELECT 1 FROM dose_logs d WHERE d.prescription_id = rx.id AND d.log_date = ?)"
            " AND NOT EXISTS (SELECT 1 FROM reminder_log r WHERE r.prescription_id = rx.id AND r.sent_on = ?)",
            (hhmm, today, today, today, today),
        ).fetchall()
        for row in rows:
            body = f"Hi {row['patient'].split()[0]},\n\nIt's time for {row['name']} ({row['dosage']})."
            if row["instructions"]:
                body += f"\n{row['instructions']}"
            body += "\n\nMark it as taken in MediPulse to keep your streak going."
            try:
                channel = deliver(row["email"], f"Time for {row['name']}", body)
            except Exception:  # a mail failure must not stop other reminders
                log.exception("Could not send reminder for prescription %s", row["id"])
                continue
            db.execute("INSERT INTO reminder_log (prescription_id, sent_on, channel) VALUES (?,?,?)",
                       (row["id"], today, channel))
            sent += 1
        db.commit()
    finally:
        db.close()
    return sent
