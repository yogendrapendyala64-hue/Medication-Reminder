"""Background job that checks for due reminders once a minute."""
import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler

from reminders import send_due_reminders

log = logging.getLogger("medipulse.scheduler")
_scheduler = None


def start_scheduler(app):
    """Start the reminder job once per process (skips the debug reloader's parent process)."""
    global _scheduler
    if _scheduler is not None or os.environ.get("ENABLE_SCHEDULER", "1") != "1":
        return None
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return None

    def job():
        try:
            send_due_reminders(app.config["DATABASE"])
        except Exception:
            log.exception("Reminder check failed")

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(job, "interval", minutes=1, id="due-reminders", max_instances=1, coalesce=True)
    _scheduler.start()
    log.info("Reminder scheduler started")
    return _scheduler
