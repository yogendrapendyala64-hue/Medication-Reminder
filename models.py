"""Queries and small business rules. Every function takes an open sqlite3 connection."""
from datetime import date, timedelta

from werkzeug.security import check_password_hash, generate_password_hash

FREQUENCIES = ["Once daily", "Twice daily", "Three times daily", "Every other day", "Weekly", "As needed"]


def today_str():
    return date.today().isoformat()


# ---------- users ----------
def create_user(db, name, email, password, role):
    cur = db.execute(
        "INSERT INTO users (name, email, password_hash, role) VALUES (?,?,?,?)",
        (name.strip(), email.strip().lower(), generate_password_hash(password), role),
    )
    db.commit()
    return cur.lastrowid


def get_user(db, user_id):
    return db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def get_user_by_email(db, email):
    return db.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()


def verify_login(db, email, password):
    user = get_user_by_email(db, email)
    if user and check_password_hash(user["password_hash"], password):
        return user
    return None


def attach_patient_profile(db, user):
    """Link a new patient account to a record the doctor already created, or make a fresh one."""
    existing = db.execute(
        "SELECT id FROM patients WHERE lower(email) = ? AND user_id IS NULL", (user["email"],)
    ).fetchone()
    if existing:
        db.execute("UPDATE patients SET user_id = ? WHERE id = ?", (user["id"], existing["id"]))
        db.commit()
        return existing["id"]
    cur = db.execute(
        "INSERT INTO patients (user_id, name, email) VALUES (?,?,?)", (user["id"], user["name"], user["email"])
    )
    db.commit()
    return cur.lastrowid


# ---------- patients ----------
def create_patient(db, doctor_id, name, email, phone="", dob="", condition=""):
    cur = db.execute(
        "INSERT INTO patients (doctor_id, name, email, phone, dob, condition) VALUES (?,?,?,?,?,?)",
        (doctor_id, name.strip(), email.strip().lower(), phone.strip(), dob.strip(), condition.strip() or "Not set"),
    )
    db.commit()
    return cur.lastrowid


def get_patient(db, patient_id):
    return db.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()


def patient_for_user(db, user_id):
    return db.execute("SELECT * FROM patients WHERE user_id = ?", (user_id,)).fetchone()


def patient_email_exists(db, email):
    return db.execute("SELECT 1 FROM patients WHERE lower(email) = ?", (email.strip().lower(),)).fetchone() is not None


def list_patients(db, query=""):
    q = f"%{query.strip().lower()}%"
    rows = db.execute(
        "SELECT * FROM patients WHERE lower(name || ' ' || email || ' ' || condition) LIKE ? ORDER BY name COLLATE NOCASE",
        (q,),
    ).fetchall()
    out = []
    for row in rows:
        item = dict(row)
        item["active_meds"] = len(list_prescriptions(db, row["id"], active_only=True))
        item["week"] = week_stats(db, row["id"], with_logs=False)
        out.append(item)
    return out


# ---------- prescriptions ----------
def is_active(rx, today=None):
    today = today or today_str()
    return not rx["end_date"] or rx["end_date"] >= today


def list_prescriptions(db, patient_id, active_only=False):
    rows = db.execute(
        "SELECT * FROM prescriptions WHERE patient_id = ? ORDER BY reminder_time, name", (patient_id,)
    ).fetchall()
    return [r for r in rows if is_active(r)] if active_only else rows


def get_prescription(db, rx_id):
    return db.execute("SELECT * FROM prescriptions WHERE id = ?", (rx_id,)).fetchone()


def add_prescription(db, patient_id, data):
    cur = db.execute(
        "INSERT INTO prescriptions (patient_id, name, dosage, reminder_time, start_date, end_date, instructions, frequency)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (patient_id, data["name"], data["dosage"], data["reminder_time"], data["start_date"],
         data["end_date"], data["instructions"], data["frequency"]),
    )
    db.commit()
    return cur.lastrowid


def update_prescription(db, rx_id, data):
    db.execute(
        "UPDATE prescriptions SET name=?, dosage=?, reminder_time=?, start_date=?, end_date=?, instructions=?, frequency=?"
        " WHERE id = ?",
        (data["name"], data["dosage"], data["reminder_time"], data["start_date"], data["end_date"],
         data["instructions"], data["frequency"], rx_id),
    )
    db.commit()


def delete_prescription(db, rx_id):
    db.execute("DELETE FROM prescriptions WHERE id = ?", (rx_id,))
    db.commit()


# ---------- dose logs ----------
def set_dose(db, rx_id, status, log_date=None):
    db.execute(
        "INSERT INTO dose_logs (prescription_id, log_date, status) VALUES (?,?,?)"
        " ON CONFLICT (prescription_id, log_date) DO UPDATE SET status = excluded.status, logged_at = datetime('now')",
        (rx_id, log_date or today_str(), status),
    )
    db.commit()


def clear_dose(db, rx_id, log_date=None):
    db.execute("DELETE FROM dose_logs WHERE prescription_id = ? AND log_date = ?", (rx_id, log_date or today_str()))
    db.commit()


def today_plan(db, patient_id):
    """Active prescriptions with today's logged status (None, 'taken' or 'missed')."""
    today = today_str()
    plan = []
    for rx in list_prescriptions(db, patient_id, active_only=True):
        log = db.execute(
            "SELECT status FROM dose_logs WHERE prescription_id = ? AND log_date = ?", (rx["id"], today)
        ).fetchone()
        item = dict(rx)
        item["status"] = log["status"] if log else None
        plan.append(item)
    return plan


def week_stats(db, patient_id, with_logs=True):
    start = (date.today() - timedelta(days=6)).isoformat()
    rows = db.execute(
        "SELECT dl.log_date, dl.status, p.name AS med, p.dosage FROM dose_logs dl"
        " JOIN prescriptions p ON p.id = dl.prescription_id"
        " WHERE p.patient_id = ? AND dl.log_date >= ? ORDER BY dl.log_date DESC, p.name",
        (patient_id, start),
    ).fetchall()
    taken = sum(1 for r in rows if r["status"] == "taken")
    total = len(rows)
    return {
        "taken": taken,
        "missed": total - taken,
        "total": total,
        "pct": round(taken / total * 100) if total else 0,
        "logs": rows if with_logs else [],
    }


def streak(db, patient_id):
    """Consecutive days (ending today or yesterday) with a taken dose and nothing missed."""
    rows = db.execute(
        "SELECT dl.log_date, dl.status FROM dose_logs dl JOIN prescriptions p ON p.id = dl.prescription_id"
        " WHERE p.patient_id = ?", (patient_id,),
    ).fetchall()
    by_day = {}
    for r in rows:
        by_day.setdefault(r["log_date"], set()).add(r["status"])
    count = 0
    for back in range(0, 120):
        day = (date.today() - timedelta(days=back)).isoformat()
        statuses = by_day.get(day)
        if statuses is None:
            if back == 0:
                continue
            break
        if "taken" in statuses and "missed" not in statuses:
            count += 1
        else:
            break
    return count


def clinic_summary(db):
    patients = list_patients(db)
    return {
        "patients": patients,
        "total": len(patients),
        "plans": sum(1 for p in patients if p["active_meds"]),
        "follow_ups": [p for p in patients if p["week"]["missed"] > 0 or not p["active_meds"]],
    }
