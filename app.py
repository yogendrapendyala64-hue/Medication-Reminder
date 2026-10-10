"""MediPulse: medication reminders for care teams and patients.

Run with:  python app.py   then open http://127.0.0.1:5000
"""
import os
import re
from datetime import date, datetime

from dotenv import load_dotenv
from flask import (Flask, abort, flash, g, redirect, render_template, request, send_file, url_for)
from markupsafe import Markup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

import database  # noqa: E402  (needs the .env values loaded first)
import models  # noqa: E402
import reports  # noqa: E402
from auth import auth_bp, login_required, role_required  # noqa: E402
from scheduler import start_scheduler  # noqa: E402

ICONS = {
    "heart": '<path d="M12 21s-7-4.6-9.3-9A5.2 5.2 0 0 1 12 6.5 5.2 5.2 0 0 1 21.3 12C19 16.4 12 21 12 21z"/>',
    "pulse": '<path d="M3 12h4l2.5-6 4 12 2.5-6H21"/>',
    "clip": '<rect x="6" y="4" width="12" height="17" rx="2"/><path d="M9 4h6v3H9zM9 12h6M9 16h4"/>',
    "cal": '<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 10h16M9 3v4M15 3v4"/>',
    "users": '<circle cx="9" cy="8" r="3.2"/><path d="M3 20c.5-3.5 3-5.2 6-5.2s5.5 1.7 6 5.2"/><path d="M16 5a3 3 0 0 1 0 6M18 14.6c1.8.6 3 2.2 3.3 5.4"/>',
    "user": '<circle cx="12" cy="8" r="3.5"/><path d="M5 20c.6-4 3.4-6 7-6s6.4 2 7 6"/>',
    "search": '<circle cx="11" cy="11" r="6.5"/><path d="m20 20-4-4"/>',
    "chev": '<path d="m9 6 6 6-6 6"/>',
    "dl": '<path d="M12 4v11m-4.5-4.5L12 15l4.5-4.5M5 20h14"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "x": '<path d="M6 6l12 12M18 6 6 18"/>',
    "out": '<path d="M9 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h3M16 8l4 4-4 4M20 12H9"/>',
    "bell": '<path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15zM10 20.5h4"/>',
    "check": '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
    "steth": '<path d="M6 3v6a4 4 0 0 0 8 0V3M10 13v2a5 5 0 0 0 10 0v-1"/><circle cx="20" cy="12" r="2"/>',
    "arrow": '<path d="M5 12h14m-5-5 5 5-5 5"/>',
    "edit": '<path d="M4 20h4L19 9l-4-4L4 16zM14 6l4 4"/>',
    "trash": '<path d="M5 7h14M10 7V4h4v3M7 7l1 13h8l1-13M10 11v6M14 11v6"/>',
}
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")
    db_name = os.environ.get("DATABASE", "medication.db")
    app.config["DATABASE"] = db_name if os.path.isabs(db_name) else os.path.join(BASE_DIR, db_name)
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    database.init_db(app.config["DATABASE"])
    database.seed_demo(app.config["DATABASE"])
    app.teardown_appcontext(database.close_db)
    app.register_blueprint(auth_bp)

    # ---------- template helpers ----------
    @app.template_global()
    def icon(name, size=None):
        style = f' style="font-size:{size}px"' if size else ""
        return Markup(f'<svg class="ic" viewBox="0 0 24 24"{style} aria-hidden="true">{ICONS[name]}</svg>')

    @app.template_filter("initials")
    def initials(name):
        parts = str(name).split()
        return ((parts[0][:1] + (parts[1][:1] if len(parts) > 1 else "")).upper()) or "?"

    @app.context_processor
    def inject():
        hour = datetime.now().hour
        return {
            "user": g.get("user"),
            "my_patient": g.get("my_patient"),
            "greeting": "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening",
            "today_label": date.today().strftime("%A %d %b"),
            "frequencies": models.FREQUENCIES,
        }

    # ---------- helpers ----------
    def patient_or_404(patient_id):
        patient = models.get_patient(database.get_db(), patient_id)
        if patient is None:
            abort(404)
        if g.user["role"] == "patient" and patient["user_id"] != g.user["id"]:
            abort(403)
        return patient

    def rx_for_doctor_or_404(rx_id):
        rx = models.get_prescription(database.get_db(), rx_id)
        if rx is None:
            abort(404)
        return rx

    def read_prescription_form():
        f = request.form
        data = {
            "name": f.get("name", "").strip(),
            "dosage": f.get("dosage", "").strip(),
            "reminder_time": f.get("reminder_time", "").strip() or "08:00",
            "start_date": f.get("start_date", "").strip() or models.today_str(),
            "end_date": f.get("end_date", "").strip(),
            "instructions": f.get("instructions", "").strip(),
            "frequency": f.get("frequency", "Once daily"),
        }
        error = None
        if not data["name"]:
            error = "Enter the medication name."
        elif not data["dosage"]:
            error = "Enter the dosage."
        elif not TIME_RE.match(data["reminder_time"]):
            error = "Use a reminder time like 08:00."
        elif data["frequency"] not in models.FREQUENCIES:
            error = "Choose a frequency from the list."
        else:
            try:
                start = date.fromisoformat(data["start_date"])
                end = date.fromisoformat(data["end_date"]) if data["end_date"] else None
                if end and end < start:
                    error = "The end date must be on or after the start date."
            except ValueError:
                error = "Use the date format YYYY-MM-DD."
        return data, error

    # ---------- public pages ----------
    @app.route("/")
    def landing():
        if g.user:
            return redirect(url_for("dashboard"))
        return render_template("landing.html")

    @app.route("/dashboard")
    @login_required
    def dashboard():
        if g.user["role"] == "doctor":
            return redirect(url_for("doctor_dashboard"))
        return redirect(url_for("patient_dashboard"))

    # ---------- doctor ----------
    @app.route("/doctor")
    @role_required("doctor")
    def doctor_dashboard():
        summary = models.clinic_summary(database.get_db())
        return render_template("doctor_dashboard.html", **summary)

    @app.route("/patients")
    @role_required("doctor")
    def patients():
        q = request.args.get("q", "")
        return render_template("patients.html", patients=models.list_patients(database.get_db(), q), q=q)

    @app.route("/patients/add", methods=["POST"])
    @role_required("doctor")
    def add_patient():
        db = database.get_db()
        f = {k: request.form.get(k, "").strip() for k in ("name", "email", "phone", "dob", "condition")}
        error = None
        if not f["name"]:
            error = "Enter the patient's full name."
        elif not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", f["email"]):
            error = "Enter a valid email address."
        elif models.patient_email_exists(db, f["email"]):
            error = "A patient with this email is already in your directory."
        elif f["dob"]:
            try:
                date.fromisoformat(f["dob"])
            except ValueError:
                error = "Use the date of birth format YYYY-MM-DD."
        if error:
            flash(error, "error")
            return redirect(request.referrer or url_for("doctor_dashboard"))
        pid = models.create_patient(db, g.user["id"], **f)
        flash(f"{f['name']} was added to your care directory.", "ok")
        return redirect(url_for("patient_details", patient_id=pid))

    @app.route("/patients/<int:patient_id>")
    @role_required("doctor")
    def patient_details(patient_id):
        db = database.get_db()
        patient = patient_or_404(patient_id)
        return render_template(
            "patient_details.html", patient=patient,
            prescriptions=models.list_prescriptions(db, patient_id),
            active_count=len(models.list_prescriptions(db, patient_id, active_only=True)),
            week=models.week_stats(db, patient_id, with_logs=False), today=models.today_str(),
        )

    @app.route("/patients/<int:patient_id>/prescriptions/add", methods=["GET", "POST"])
    @role_required("doctor")
    def add_prescription(patient_id):
        patient = patient_or_404(patient_id)
        form = {"reminder_time": "08:00", "start_date": models.today_str(), "end_date": "", "frequency": "Once daily"}
        if request.method == "POST":
            form, error = read_prescription_form()
            if error:
                flash(error, "error")
            else:
                models.add_prescription(database.get_db(), patient_id, form)
                flash(f"{form['name']} was added to {patient['name']}'s plan.", "ok")
                return redirect(url_for("patient_details", patient_id=patient_id))
        return render_template("add_prescription.html", patient=patient, form=form)

    @app.route("/prescriptions/<int:rx_id>/edit", methods=["GET", "POST"])
    @role_required("doctor")
    def edit_prescription(rx_id):
        rx = rx_for_doctor_or_404(rx_id)
        patient = patient_or_404(rx["patient_id"])
        form = dict(rx)
        if request.method == "POST":
            form, error = read_prescription_form()
            if error:
                flash(error, "error")
            else:
                models.update_prescription(database.get_db(), rx_id, form)
                flash("Prescription updated.", "ok")
                return redirect(url_for("patient_details", patient_id=patient["id"]))
        return render_template("edit_prescription.html", patient=patient, rx=rx, form=form)

    @app.route("/prescriptions/<int:rx_id>/delete", methods=["POST"])
    @role_required("doctor")
    def delete_prescription(rx_id):
        rx = rx_for_doctor_or_404(rx_id)
        models.delete_prescription(database.get_db(), rx_id)
        flash(f"{rx['name']} was removed.", "ok")
        return redirect(url_for("patient_details", patient_id=rx["patient_id"]))

    # ---------- patient ----------
    @app.route("/me")
    @role_required("patient")
    def patient_dashboard():
        db = database.get_db()
        patient = g.my_patient
        if patient is None:
            abort(404)
        return render_template(
            "patient_dashboard.html", patient=patient, plan=models.today_plan(db, patient["id"]),
            week=models.week_stats(db, patient["id"], with_logs=False), streak=models.streak(db, patient["id"]),
        )

    @app.route("/me/dose/<int:rx_id>/<status>", methods=["POST"])
    @role_required("patient")
    def log_dose(rx_id, status):
        db = database.get_db()
        rx = models.get_prescription(db, rx_id)
        if rx is None or g.my_patient is None or rx["patient_id"] != g.my_patient["id"]:
            abort(404)
        if status == "undo":
            models.clear_dose(db, rx_id)
        elif status in ("taken", "missed"):
            models.set_dose(db, rx_id, status)
        else:
            abort(400)
        return redirect(url_for("patient_dashboard") + "#today")

    # ---------- reports ----------
    @app.route("/patients/<int:patient_id>/report")
    @login_required
    def report_view(patient_id):
        patient_or_404(patient_id)
        data = reports.build_report(database.get_db(), patient_id)
        back = url_for("patient_details", patient_id=patient_id) if g.user["role"] == "doctor" else url_for("patient_dashboard")
        return render_template("report.html", report=data, back_url=back)

    @app.route("/patients/<int:patient_id>/report.pdf")
    @login_required
    def report_pdf(patient_id):
        patient_or_404(patient_id)
        data = reports.build_report(database.get_db(), patient_id)
        path = reports.generate_pdf(data)
        return send_file(path, mimetype="application/pdf", as_attachment=True,
                         download_name=reports.report_filename(data["patient"]))

    # ---------- errors ----------
    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("error.html", code=403, message="You don't have access to that page."), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("error.html", code=404, message="That page could not be found."), 404

    return app


app = create_app()

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.debug = debug
    start_scheduler(app)
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=debug)
