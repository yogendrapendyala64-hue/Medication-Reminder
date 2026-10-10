"""Sign-in, registration, sessions and access decorators."""
import re
from functools import wraps

from flask import Blueprint, abort, flash, g, redirect, render_template, request, session, url_for

import models
from database import get_db, seed_demo

auth_bp = Blueprint("auth", __name__)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DEMO_ACCOUNTS = {"doctor": "doctor@medipulse.app", "patient": "jordan@medipulse.app"}


@auth_bp.before_app_request
def load_user():
    user_id = session.get("user_id")
    g.user = models.get_user(get_db(), user_id) if user_id else None
    g.my_patient = None
    if g.user and g.user["role"] == "patient":
        g.my_patient = models.patient_for_user(get_db(), g.user["id"])


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped


def role_required(role):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if g.user is None:
                return redirect(url_for("auth.login"))
            if g.user["role"] != role:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def start_session(user):
    session.clear()
    session["user_id"] = user["id"]


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        user = models.verify_login(get_db(), email, password) if email and password else None
        if user:
            start_session(user)
            return redirect(url_for("dashboard"))
        flash("Email or password is incorrect.", "error")
    return render_template("login.html", email=request.form.get("email", ""))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("dashboard"))
    form = {"name": "", "email": "", "role": "patient"}
    if request.method == "POST":
        form = {k: request.form.get(k, "").strip() for k in ("name", "email", "role")}
        password = request.form.get("password", "")
        db = get_db()
        error = None
        if not form["name"]:
            error = "Enter your full name."
        elif not EMAIL_RE.match(form["email"]):
            error = "Enter a valid email address."
        elif len(password) < 6:
            error = "Use at least 6 characters for the password."
        elif form["role"] not in ("doctor", "patient"):
            error = "Choose whether you are a patient or a care provider."
        elif models.get_user_by_email(db, form["email"]):
            error = "That email already has an account. Sign in instead."
        if error:
            flash(error, "error")
        else:
            user_id = models.create_user(db, form["name"], form["email"], password, form["role"])
            user = models.get_user(db, user_id)
            if form["role"] == "patient":
                models.attach_patient_profile(db, user)
            start_session(user)
            flash("Your account is ready.", "ok")
            return redirect(url_for("dashboard"))
    return render_template("register.html", form=form)


@auth_bp.route("/demo/<role>", methods=["POST"])
def demo(role):
    if role not in DEMO_ACCOUNTS:
        abort(404)
    db = get_db()
    user = models.get_user_by_email(db, DEMO_ACCOUNTS[role])
    if user is None:  # database was emptied; rebuild the demo data
        from flask import current_app
        seed_demo(current_app.config["DATABASE"])
        user = models.get_user_by_email(db, DEMO_ACCOUNTS[role])
    start_session(user)
    return redirect(url_for("dashboard"))


@auth_bp.route("/logout", methods=["POST", "GET"])
def logout():
    session.clear()
    return redirect(url_for("landing"))
