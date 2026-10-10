"""SQLite helpers: connections, schema set-up and demo data."""
import os
import sqlite3
from datetime import date, timedelta

from flask import current_app, g
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")


def connect(path):
    """Open a standalone connection (used by the scheduler and set-up code)."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    """Per-request connection, stored on flask.g."""
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(path):
    conn = connect(path)
    with open(SCHEMA_PATH, encoding="utf-8") as fh:
        conn.executescript(fh.read())
    conn.commit()
    conn.close()


def seed_demo(path):
    """Create the demo doctor, demo patient and sample care plans if the database is empty."""
    conn = connect(path)
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
        conn.close()
        return
    pw = generate_password_hash("demo1234")
    doc = conn.execute(
        "INSERT INTO users (name, email, password_hash, role) VALUES (?,?,?,?)",
        ("Dr. Maya Chen", "doctor@medipulse.app", pw, "doctor"),
    ).lastrowid
    jordan_user = conn.execute(
        "INSERT INTO users (name, email, password_hash, role) VALUES (?,?,?,?)",
        ("Jordan Williams", "jordan@medipulse.app", pw, "patient"),
    ).lastrowid

    people = [
        ("Jordan Williams", "jordan@medipulse.app", "(555) 014-2290", "1984-06-18", "Hypertension", jordan_user),
        ("Priya Nair", "priya.nair@example.com", "(555) 018-7741", "1991-03-02", "Type 2 diabetes", None),
        ("Marcus Reed", "marcus.reed@example.com", "(555) 011-9035", "1975-11-27", "Asthma", None),
        ("Elena Rossi", "elena.rossi@example.com", "(555) 016-3358", "1968-09-09", "Hypothyroidism", None),
    ]
    ids = []
    for name, email, phone, dob, cond, uid in people:
        ids.append(conn.execute(
            "INSERT INTO patients (user_id, doctor_id, name, email, phone, dob, condition) VALUES (?,?,?,?,?,?,?)",
            (uid, doc, name, email, phone, dob, cond),
        ).lastrowid)

    today = date.today()
    far = (today + timedelta(days=120)).isoformat()
    meds = [
        (ids[0], "Lisinopril", "10 mg", "08:00", 30, "Take with water before breakfast", "Once daily", [1, 2, 3], [4]),
        (ids[0], "Metoprolol", "25 mg", "09:00", 30, "Take with water", "Once daily", [1, 2, 4], [3]),
        (ids[0], "Aspirin", "75 mg", "09:00", 14, "Follow your prescribed care plan", "Once daily", [1, 3], [2]),
        (ids[0], "Vitamin D3", "1000 IU", "20:00", 14, "Take with dinner", "Once daily", [1, 2, 3], []),
        (ids[1], "Metformin", "500 mg", "08:30", 60, "Take with food", "Twice daily", [1, 2, 3, 4], []),
        (ids[2], "Salbutamol inhaler", "2 puffs", "07:30", 40, "Rinse mouth after use", "As needed", [1, 2], [3]),
    ]
    for pid, name, dose, t, back, ins, freq, taken, missed in meds:
        rx = conn.execute(
            "INSERT INTO prescriptions (patient_id, name, dosage, reminder_time, start_date, end_date, instructions, frequency)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (pid, name, dose, t, (today - timedelta(days=back)).isoformat(), far, ins, freq),
        ).lastrowid
        for n in taken:
            conn.execute("INSERT INTO dose_logs (prescription_id, log_date, status) VALUES (?,?,?)",
                         (rx, (today - timedelta(days=n)).isoformat(), "taken"))
        for n in missed:
            conn.execute("INSERT INTO dose_logs (prescription_id, log_date, status) VALUES (?,?,?)",
                         (rx, (today - timedelta(days=n)).isoformat(), "missed"))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    # python database.py  ->  create medication.db with demo data
    target = os.path.join(BASE_DIR, os.environ.get("DATABASE", "medication.db"))
    init_db(target)
    seed_demo(target)
    print("Database ready:", target)
