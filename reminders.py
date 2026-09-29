from datetime import datetime

from models import get_patient_doses


def get_due_reminders(patient_id):

    now = datetime.now()

    doses = get_patient_doses(
        patient_id,
        days=1
    )

    due = []

    for dose in doses:

        if dose["status"] != "pending":
            continue

        difference = abs(
            (
                dose["scheduled_at"] - now
            ).total_seconds()
        )

        # 15 minute reminder window
        if difference <= 15 * 60:
            due.append(dose)

    return due