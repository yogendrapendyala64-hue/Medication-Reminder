# MediPulse

Medication reminders for care teams and patients (Flask + SQLite).

## Run it
```
python -m venv .venv
.venv\Scripts\activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

## Demo logins
- Doctor: doctor@medipulse.app / demo1234
- Patient: jordan@medipulse.app / demo1234

## Files
- app.py: routes and app set-up
- auth.py: sign-in, register, access control
- database.py, schema.sql: SQLite connection, tables, demo data
- models.py: queries and adherence/streak rules
- reports.py: weekly report data and PDF (saved in reports/)
- reminders.py, scheduler.py: checks every minute and emails patients whose dose is due
- templates/, static/: pages, styles, small front-end script
- .env: SECRET_KEY, database name, optional SMTP settings

## Notes
- Reminders are only logged to the console until SMTP_HOST is set in .env.
- Delete medication.db to rebuild it with fresh demo data (the sample dose history is dated from the day it was created).
- Change SECRET_KEY in .env before using this for anything real.
