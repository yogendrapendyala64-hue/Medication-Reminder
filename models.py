from datetime import datetime, timedelta

from database import query, execute


# ---------------------------------------------------------
# PATIENT
# ---------------------------------------------------------

def get_patient(patient_id):

    return query(
        """
        SELECT
            id,
            full_name,
            email,
            created_at
        FROM users
        WHERE id = %s
        AND role = 'patient'
        """,
        (patient_id,),
        fetchall=False
    )


def get_all_patients():

    return query(
        """
        SELECT
            id,
            full_name,
            email
        FROM users
        WHERE role = 'patient'
        ORDER BY full_name
        """
    )


def get_patients_for_doctor(doctor_id):

    return query(
        """
        SELECT DISTINCT
            u.id,
            u.full_name,
            u.email
        FROM users u
        INNER JOIN prescriptions p
            ON p.patient_id = u.id
        WHERE p.doctor_id = %s
        AND u.role = 'patient'
        ORDER BY u.full_name
        """,
        (doctor_id,)
    )


# ---------------------------------------------------------
# PRESCRIPTIONS
# ---------------------------------------------------------

def get_prescriptions_for_patient(patient_id):

    return query(
        """
        SELECT
            p.*,
            d.full_name AS doctor_name
        FROM prescriptions p
        INNER JOIN users d
            ON d.id = p.doctor_id
        WHERE p.patient_id = %s
        ORDER BY p.end_date DESC, p.id DESC
        """,
        (patient_id,)
    )


def get_prescriptions_for_doctor(doctor_id):

    return query(
        """
        SELECT
            p.*,
            u.full_name AS patient_name,
            u.email AS patient_email
        FROM prescriptions p
        INNER JOIN users u
            ON u.id = p.patient_id
        WHERE p.doctor_id = %s
        ORDER BY p.end_date DESC, p.id DESC
        """,
        (doctor_id,)
    )


def doctor_has_patient(doctor_id, patient_id):

    result = query(
        """
        SELECT id
        FROM prescriptions
        WHERE doctor_id = %s
        AND patient_id = %s
        LIMIT 1
        """,
        (
            doctor_id,
            patient_id
        ),
        fetchall=False
    )

    return bool(result)


# ---------------------------------------------------------
# CREATE PRESCRIPTION
# ---------------------------------------------------------

def create_prescription(
    doctor_id,
    patient_id,
    medicine_name,
    dose,
    frequency_type,
    fixed_times,
    interval_hours,
    start_date,
    end_date,
    notes
):

    prescription_id = execute(
        """
        INSERT INTO prescriptions
        (
            doctor_id,
            patient_id,
            medicine_name,
            dose,
            frequency_type,
            fixed_times,
            interval_hours,
            start_date,
            end_date,
            notes
        )
        VALUES
        (
            %s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s
        )
        """,
        (
            doctor_id,
            patient_id,
            medicine_name,
            dose,
            frequency_type,
            fixed_times,
            interval_hours,
            start_date,
            end_date,
            notes
        )
    )

    generate_slots(prescription_id)

    return prescription_id


# ---------------------------------------------------------
# GENERATE MEDICATION REMINDER SLOTS
# ---------------------------------------------------------

def generate_slots(prescription_id):

    prescription = query(
        """
        SELECT *
        FROM prescriptions
        WHERE id = %s
        """,
        (prescription_id,),
        fetchall=False
    )

    if not prescription:
        return

    start_date = prescription["start_date"]
    end_date = prescription["end_date"]

    # Fixed clock times
    if prescription["frequency_type"] == "fixed_times":

        times = [
            x.strip()
            for x in (
                prescription["fixed_times"] or ""
            ).split(",")
            if x.strip()
        ]

        current_date = start_date

        while current_date <= end_date:

            for time_text in times:

                try:

                    parts = time_text.split(":")

                    hour = int(parts[0])
                    minute = int(parts[1])

                    scheduled = datetime(
                        current_date.year,
                        current_date.month,
                        current_date.day,
                        hour,
                        minute
                    )

                    execute(
                        """
                        INSERT IGNORE INTO dose_slots
                        (
                            prescription_id,
                            scheduled_at
                        )
                        VALUES (%s,%s)
                        """,
                        (
                            prescription_id,
                            scheduled
                        )
                    )

                except (ValueError, IndexError):
                    continue

            current_date += timedelta(days=1)

    # Every N hours
    else:

        hours = int(
            prescription["interval_hours"] or 8
        )

        current = datetime.combine(
            start_date,
            datetime.min.time()
        )

        end_datetime = datetime.combine(
            end_date,
            datetime.max.time()
        )

        while current <= end_datetime:

            execute(
                """
                INSERT IGNORE INTO dose_slots
                (
                    prescription_id,
                    scheduled_at
                )
                VALUES (%s,%s)
                """,
                (
                    prescription_id,
                    current
                )
            )

            current += timedelta(hours=hours)


# ---------------------------------------------------------
# DOSES
# ---------------------------------------------------------

def mark_overdue_as_missed(patient_id=None):

    extra_condition = ""
    params = []

    if patient_id is not None:

        extra_condition = """
            AND p.patient_id = %s
        """

        params.append(patient_id)

    slots = query(
        f"""
        SELECT
            s.id,
            p.patient_id
        FROM dose_slots s
        INNER JOIN prescriptions p
            ON p.id = s.prescription_id
        WHERE s.status = 'pending'
        AND s.scheduled_at <
            NOW() - INTERVAL 30 MINUTE
        {extra_condition}
        """,
        tuple(params)
    )

    for slot in slots:

        execute(
            """
            UPDATE dose_slots
            SET status = 'missed'
            WHERE id = %s
            AND status = 'pending'
            """,
            (slot["id"],)
        )

        execute(
            """
            INSERT INTO dose_logs
            (
                dose_slot_id,
                patient_id,
                status
            )
            SELECT
                %s,
                %s,
                'missed'
            WHERE NOT EXISTS
            (
                SELECT 1
                FROM dose_logs
                WHERE dose_slot_id = %s
            )
            """,
            (
                slot["id"],
                slot["patient_id"],
                slot["id"]
            )
        )


def get_patient_doses(
    patient_id,
    days=7
):

    mark_overdue_as_missed(patient_id)

    return query(
        """
        SELECT
            s.id,
            s.scheduled_at,
            s.status,
            s.taken_at,

            p.id AS prescription_id,
            p.medicine_name,
            p.dose,
            p.frequency_type

        FROM dose_slots s

        INNER JOIN prescriptions p
            ON p.id = s.prescription_id

        WHERE p.patient_id = %s

        AND s.scheduled_at >=
            NOW() - INTERVAL 1 DAY

        AND s.scheduled_at <
            NOW() + INTERVAL %s DAY

        ORDER BY s.scheduled_at ASC
        """,
        (
            patient_id,
            days
        )
    )


def log_dose(
    slot_id,
    patient_id,
    status
):

    if status not in (
        "taken",
        "missed"
    ):
        return False

    slot = query(
        """
        SELECT
            s.id,
            s.status,
            p.patient_id
        FROM dose_slots s

        INNER JOIN prescriptions p
            ON p.id = s.prescription_id

        WHERE s.id = %s
        """,
        (slot_id,),
        fetchall=False
    )

    if not slot:
        return False

    if slot["patient_id"] != patient_id:
        return False

    execute(
        """
        UPDATE dose_slots
        SET
            status = %s,
            taken_at =
                CASE
                    WHEN %s = 'taken'
                    THEN NOW()
                    ELSE NULL
                END
        WHERE id = %s
        """,
        (
            status,
            status,
            slot_id
        )
    )

    execute(
        """
        INSERT INTO dose_logs
        (
            dose_slot_id,
            patient_id,
            status
        )
        VALUES (%s,%s,%s)
        """,
        (
            slot_id,
            patient_id,
            status
        )
    )

    return True


# ---------------------------------------------------------
# DASHBOARD STATISTICS
# ---------------------------------------------------------

def get_patient_statistics(patient_id):

    rows = get_patient_doses(
        patient_id,
        7
    )

    scheduled = len(rows)

    taken = sum(
        1
        for row in rows
        if row["status"] == "taken"
    )

    missed = sum(
        1
        for row in rows
        if row["status"] == "missed"
    )

    pending = sum(
        1
        for row in rows
        if row["status"] == "pending"
    )

    adherence = (
        (taken / scheduled) * 100
        if scheduled
        else 0
    )

    return {
        "scheduled": scheduled,
        "taken": taken,
        "missed": missed,
        "pending": pending,
        "adherence": round(adherence, 1)
    }