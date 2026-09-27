from flask import Flask, render_template, request, redirect, url_for, session, flash
from database import get_connection
from functools import wraps


# =========================================================
# FLASK APPLICATION
# =========================================================

app = Flask(__name__)

app.secret_key = "medication_reminder_secret_key_2026"


# =========================================================
# LOGIN REQUIRED
# =========================================================

def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:
            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return wrapper


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def home():

    if "user_id" not in session:
        return redirect(url_for("login"))

    role = session.get("role")

    if role == "doctor":
        return redirect(url_for("doctor_dashboard"))

    elif role == "patient":
        return redirect(url_for("patient_dashboard"))

    else:
        return redirect(url_for("dashboard"))


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:

            flash(
                "Please enter username and password.",
                "error"
            )

            return render_template("login.html")

        connection = get_connection()

        if connection is None:

            flash(
                "Database connection failed.",
                "error"
            )

            return render_template("login.html")

        cursor = connection.cursor(dictionary=True)

        try:

            cursor.execute(
                """
                SELECT *
                FROM users
                WHERE username = %s
                AND password = %s
                """,
                (username, password)
            )

            user = cursor.fetchone()

        except Exception as e:

            print("Login error:", e)

            user = None

        finally:

            cursor.close()
            connection.close()

        if user:

            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            if user["role"] == "doctor":

                return redirect(
                    url_for("doctor_dashboard")
                )

            elif user["role"] == "patient":

                return redirect(
                    url_for("patient_dashboard")
                )

            else:

                return redirect(
                    url_for("dashboard")
                )

        else:

            flash(
                "Invalid username or password.",
                "error"
            )

    return render_template("login.html")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/dashboard")
@login_required
def dashboard():

    connection = get_connection()

    if connection is None:
        return "Database connection failed."

    cursor = connection.cursor(dictionary=True)

    # Get patients
    cursor.execute(
        """
        SELECT *
        FROM patients
        ORDER BY id DESC
        """
    )

    patients = cursor.fetchall()

    # Get prescriptions
    cursor.execute(
        """
        SELECT
            prescriptions.*,
            patients.name AS patient_name
        FROM prescriptions
        LEFT JOIN patients
        ON prescriptions.patient_id = patients.id
        ORDER BY prescriptions.id DESC
        """
    )

    prescriptions = cursor.fetchall()

    # Patient count
    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM patients
        """
    )

    patient_count = cursor.fetchone()["total"]

    # Prescription count
    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM prescriptions
        """
    )

    prescription_count = cursor.fetchone()["total"]

    cursor.close()
    connection.close()

    return render_template(
        "patient_dashboard.html",
        patients=patients,
        prescriptions=prescriptions,
        patient_count=patient_count,
        prescription_count=prescription_count
    )


# =========================================================
# DOCTOR DASHBOARD
# =========================================================

@app.route("/doctor_dashboard")
@login_required
def doctor_dashboard():

    connection = get_connection()

    if connection is None:
        return "Database connection failed."

    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM patients
        ORDER BY id DESC
        """
    )

    patients = cursor.fetchall()

    cursor.execute(
        """
        SELECT
            prescriptions.*,
            patients.name AS patient_name
        FROM prescriptions
        LEFT JOIN patients
        ON prescriptions.patient_id = patients.id
        ORDER BY prescriptions.id DESC
        """
    )

    prescriptions = cursor.fetchall()

    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM patients
        """
    )

    patient_count = cursor.fetchone()["total"]

    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM prescriptions
        """
    )

    prescription_count = cursor.fetchone()["total"]

    cursor.close()
    connection.close()

    return render_template(
        "doctor_dashboard.html",
        patients=patients,
        prescriptions=prescriptions,
        patient_count=patient_count,
        prescription_count=prescription_count
    )


# =========================================================
# PATIENT DASHBOARD
# =========================================================

@app.route("/patient_dashboard")
@login_required
def patient_dashboard():

    connection = get_connection()

    if connection is None:
        return "Database connection failed."

    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM patients
        ORDER BY id DESC
        """
    )

    patients = cursor.fetchall()

    cursor.execute(
        """
        SELECT
            prescriptions.*,
            patients.name AS patient_name
        FROM prescriptions
        LEFT JOIN patients
        ON prescriptions.patient_id = patients.id
        ORDER BY prescriptions.id DESC
        """
    )

    prescriptions = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "patient_dashboard.html",
        patients=patients,
        prescriptions=prescriptions
    )


# =========================================================
# PATIENT LIST
# =========================================================

@app.route("/patients")
@login_required
def patients():

    connection = get_connection()

    if connection is None:
        return "Database connection failed."

    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM patients
        ORDER BY id DESC
        """
    )

    patients_data = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "patients.html",
        patients=patients_data
    )


# =========================================================
# ADD PATIENT
# =========================================================

@app.route("/add_patient", methods=["GET", "POST"])
@login_required
def add_patient():

    if request.method == "POST":

        name = request.form.get(
            "name", ""
        ).strip()

        age = request.form.get("age")

        gender = request.form.get(
            "gender", ""
        ).strip()

        phone = request.form.get(
            "phone", ""
        ).strip()

        email = request.form.get(
            "email", ""
        ).strip()

        if not name:

            flash(
                "Patient name is required.",
                "error"
            )

            return redirect(
                url_for("patients")
            )

        connection = get_connection()

        if connection is None:
            return "Database connection failed."

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO patients
            (
                name,
                age,
                gender,
                phone,
                email
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                name,
                age if age else None,
                gender,
                phone,
                email
            )
        )

        connection.commit()

        cursor.close()
        connection.close()

        flash(
            "Patient added successfully.",
            "success"
        )

        return redirect(
            url_for("patients")
        )

    return render_template(
        "patients.html"
    )


# =========================================================
# PATIENT DETAILS
# =========================================================

@app.route("/patient/<int:patient_id>")
@login_required
def patient_details(patient_id):

    connection = get_connection()

    if connection is None:
        return "Database connection failed."

    cursor = connection.cursor(dictionary=True)

    # Get patient
    cursor.execute(
        """
        SELECT *
        FROM patients
        WHERE id = %s
        """,
        (patient_id,)
    )

    patient = cursor.fetchone()

    if patient is None:

        cursor.close()
        connection.close()

        flash(
            "Patient not found.",
            "error"
        )

        return redirect(
            url_for("patients")
        )

    # Get prescriptions
    cursor.execute(
        """
        SELECT *
        FROM prescriptions
        WHERE patient_id = %s
        ORDER BY id DESC
        """,
        (patient_id,)
    )

    prescriptions = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "patient_details.html",
        patient=patient,
        prescriptions=prescriptions
    )


# =========================================================
# DELETE PATIENT
# =========================================================

@app.route("/delete_patient/<int:patient_id>")
@login_required
def delete_patient(patient_id):

    connection = get_connection()

    if connection is None:
        return "Database connection failed."

    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM patients
        WHERE id = %s
        """,
        (patient_id,)
    )

    connection.commit()

    cursor.close()
    connection.close()

    flash(
        "Patient deleted successfully.",
        "success"
    )

    return redirect(
        url_for("patients")
    )


# =========================================================
# ADD PRESCRIPTION
# =========================================================

@app.route(
    "/add_prescription",
    methods=["GET", "POST"]
)
@login_required
def add_prescription():

    connection = get_connection()

    if connection is None:
        return "Database connection failed."

    cursor = connection.cursor(dictionary=True)

    # Get all patients
    cursor.execute(
        """
        SELECT *
        FROM patients
        ORDER BY name
        """
    )

    patients_data = cursor.fetchall()

    if request.method == "POST":

        patient_id = request.form.get(
            "patient_id"
        )

        medicine_name = request.form.get(
            "medicine_name",
            ""
        ).strip()

        dosage = request.form.get(
            "dosage",
            ""
        ).strip()

        frequency = request.form.get(
            "frequency",
            ""
        ).strip()

        start_date = request.form.get(
            "start_date"
        )

        end_date = request.form.get(
            "end_date"
        )

        reminder_time = request.form.get(
            "reminder_time"
        )

        if not patient_id or not medicine_name:

            cursor.close()
            connection.close()

            flash(
                "Patient and medicine name are required.",
                "error"
            )

            return render_template(
                "add_prescription.html",
                patients=patients_data
            )

        cursor.execute(
            """
            INSERT INTO prescriptions
            (
                patient_id,
                medicine_name,
                dosage,
                frequency,
                start_date,
                end_date,
                reminder_time
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                patient_id,
                medicine_name,
                dosage,
                frequency,
                start_date if start_date else None,
                end_date if end_date else None,
                reminder_time if reminder_time else None
            )
        )

        connection.commit()

        cursor.close()
        connection.close()

        flash(
            "Prescription added successfully.",
            "success"
        )

        return redirect(
            url_for(
                "patient_details",
                patient_id=patient_id
            )
        )

    cursor.close()
    connection.close()

    return render_template(
        "add_prescription.html",
        patients=patients_data
    )


# =========================================================
# EDIT PRESCRIPTION
# =========================================================

@app.route(
    "/edit_prescription/<int:prescription_id>",
    methods=["GET", "POST"]
)
@login_required
def edit_prescription(prescription_id):

    connection = get_connection()

    if connection is None:
        return "Database connection failed."

    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM prescriptions
        WHERE id = %s
        """,
        (prescription_id,)
    )

    prescription = cursor.fetchone()

    if prescription is None:

        cursor.close()
        connection.close()

        flash(
            "Prescription not found.",
            "error"
        )

        return redirect(
            url_for("dashboard")
        )

    if request.method == "POST":

        medicine_name = request.form.get(
            "medicine_name",
            ""
        ).strip()

        dosage = request.form.get(
            "dosage",
            ""
        ).strip()

        frequency = request.form.get(
            "frequency",
            ""
        ).strip()

        start_date = request.form.get(
            "start_date"
        )

        end_date = request.form.get(
            "end_date"
        )

        reminder_time = request.form.get(
            "reminder_time"
        )

        cursor.execute(
            """
            UPDATE prescriptions
            SET
                medicine_name = %s,
                dosage = %s,
                frequency = %s,
                start_date = %s,
                end_date = %s,
                reminder_time = %s
            WHERE id = %s
            """,
            (
                medicine_name,
                dosage,
                frequency,
                start_date if start_date else None,
                end_date if end_date else None,
                reminder_time if reminder_time else None,
                prescription_id
            )
        )

        connection.commit()

        patient_id = prescription["patient_id"]

        cursor.close()
        connection.close()

        flash(
            "Prescription updated successfully.",
            "success"
        )

        return redirect(
            url_for(
                "patient_details",
                patient_id=patient_id
            )
        )

    cursor.close()
    connection.close()

    return render_template(
        "edit_prescription.html",
        prescription=prescription
    )


# =========================================================
# DELETE PRESCRIPTION
# =========================================================

@app.route(
    "/delete_prescription/<int:prescription_id>"
)
@login_required
def delete_prescription(prescription_id):

    connection = get_connection()

    if connection is None:
        return "Database connection failed."

    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT patient_id
        FROM prescriptions
        WHERE id = %s
        """,
        (prescription_id,)
    )

    prescription = cursor.fetchone()

    if prescription is None:

        cursor.close()
        connection.close()

        flash(
            "Prescription not found.",
            "error"
        )

        return redirect(
            url_for("dashboard")
        )

    patient_id = prescription["patient_id"]

    cursor.execute(
        """
        DELETE FROM prescriptions
        WHERE id = %s
        """,
        (prescription_id,)
    )

    connection.commit()

    cursor.close()
    connection.close()

    flash(
        "Prescription deleted successfully.",
        "success"
    )

    return redirect(
        url_for(
            "patient_details",
            patient_id=patient_id
        )
    )


# =========================================================
# REPORT
# =========================================================

@app.route("/report")
@login_required
def report():

    connection = get_connection()

    if connection is None:
        return "Database connection failed."

    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            patients.id AS patient_id,
            patients.name AS patient_name,
            patients.age,
            patients.gender,
            patients.phone,
            patients.email,

            prescriptions.id AS prescription_id,
            prescriptions.medicine_name,
            prescriptions.dosage,
            prescriptions.frequency,
            prescriptions.start_date,
            prescriptions.end_date,
            prescriptions.reminder_time

        FROM patients

        LEFT JOIN prescriptions
        ON patients.id = prescriptions.patient_id

        ORDER BY patients.id DESC
        """
    )

    data = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "report.html",
        data=data
    )


# =========================================================
# DATABASE TEST PAGE
# =========================================================

@app.route("/test")
def test():

    connection = get_connection()

    if connection is None:

        return """
        <h2>MySQL Connection Failed</h2>
        """

    cursor = connection.cursor()

    cursor.execute(
        "SELECT DATABASE()"
    )

    database_name = cursor.fetchone()[0]

    cursor.close()
    connection.close()

    return f"""
    <h2>Medication Reminder App</h2>
    <p>Flask is running successfully.</p>
    <p>MySQL is connected successfully.</p>
    <p>Database: {database_name}</p>
    """


# =========================================================
# START FLASK
# =========================================================

if __name__ == "__main__":

    print("----------------------------------------")
    print("Medication Reminder App")
    print("----------------------------------------")

    connection = get_connection()

    if connection is not None:

        print("MySQL connection: SUCCESS")

        connection.close()

        print("Starting Flask server...")
        print("Open: http://127.0.0.1:5000")

        app.run(
            host="127.0.0.1",
            port=5000,
            debug=True
        )

    else:

        print("MySQL connection: FAILED")
        print("Check database.py and MySQL Server.")