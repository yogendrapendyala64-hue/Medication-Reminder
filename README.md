# Medication-Reminder
# Patient Medication Reminder and Adherence Log

**Digital Health • Python Project**

Scheduling dose reminders, logging adherence, and reporting progress to the
doctor — built end-to-end in Python.

---

## Problem Statement

Patients on multi-dose prescriptions often forget doses or lose track of
what they've already taken. Doctors, in turn, have no easy record of how
well a patient is following their prescribed schedule between visits.

| Issue | Description |
|---|---|
| **Missed Doses** | No automatic reminders mean doses are easy to forget, especially on multi-times-a-day schedules. |
| **No Adherence Record** | Taken / missed doses aren't logged anywhere the patient or doctor can review later. |
| **Blind Doctor Visits** | Doctors must rely on the patient's memory instead of real data when reviewing treatment. |

## Project Objectives

- **Build a prescription schedule engine** — convert a doctor's
  prescription into a precise set of daily reminder times.
- **Deliver timely dose reminders** — notify the patient at the right
  moment for every scheduled dose, every day.
- **Log every dose as taken or missed** — give the patient a one-tap way
  to record what actually happened.
- **Generate a weekly adherence report** — summarize adherence trends
  into a clear report the doctor can review.
- **Stay correct across time zones** — keep reminder times accurate even
  when the patient's phone changes time zone.
- **Support varied dosing intervals** — handle both fixed clock-time
  schedules and rolling every-N-hour schedules.

## Core Use Cases

1. **Schedule Dose Reminders & Log Adherence** — Parse a prescription
   (drug, dose, frequency, duration) into a reminder schedule. At each
   scheduled time, notify the patient and record their response as
   Taken or Missed in a persistent log.
2. **Generate a Weekly Adherence Report** — Aggregate a week of
   taken/missed logs per medicine into adherence percentages and
   trends, then export a clear summary the patient can share with
   their doctor.

## System Architecture

Data flows through the system as follows:

```
Prescription Input → Scheduler Engine → Reminder Service → Adherence Log → Weekly Report
   (drug, dose,         (builds dose        (fires             (stores taken/     (summarized
   frequency,           times: clock-       notifications      missed events      for the
   duration)            based / interval)   at due times)      with timestamps)   doctor)
```

Built as three layers:

- **Data layer** — SQLite (via Python's `sqlite3` module) storing
  prescriptions, schedules, and dose logs
- **Logic layer** — schedule generation, timer/reminder checks, report
  aggregation
- **Interface layer** — CLI or Tkinter GUI for reminders, logging taps,
  and reports

## Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Core Language | Python 3 | Scheduling logic, CLI/app control flow, report generation |
| Data Storage | SQLite (`sqlite3`) | Lightweight local database for prescriptions and dose logs |
| Scheduling | `datetime`, `schedule` / `APScheduler` | Computing dose times and triggering reminders |
| Interface | Tkinter (GUI) or CLI menu | Patient-facing reminder pop-ups and adherence entry |
| Reporting | `pandas` + `matplotlib` (optional) | Weekly adherence percentages and simple trend charts |
| Time-zone handling | `zoneinfo` / `pytz` | Correct conversions and daylight-saving edge cases |

## Database Design

Three tables cover the whole workflow:

**Prescriptions**
- `prescription_id` (PK)
- `patient_id`
- `medicine_name`
- `frequency_type` (`FIXED_TIMES` or `INTERVAL`)
- `interval_hours` (for `INTERVAL` schedules)
- `start_date` / `end_date`
- `notes` (optional)

**ScheduleSlots**
- `slot_id` (PK)
- `prescription_id` (FK)
- `scheduled_time` (local, for display)
- `scheduled_time` (UTC, source of truth)
- `timezone_at_creation`

**DoseLogs**
- `log_id` (PK)
- `slot_id` (FK)
- `dose`
- `status` — `taken` / `missed`
- `logged_at` (timestamp)

Relationships: one Prescription → many ScheduleSlots (1:N), one
ScheduleSlot → many DoseLogs (1:N).

## Scheduling Logic

Two different clock strategies share one schedule table, selected by a
`frequency_type` flag on each prescription:

### Fixed Clock-Time Schedule (`FIXED_TIMES`)

For patterns like "twice daily" or "3 times a day." Anchored to fixed
times of day (e.g. 08:00 / 20:00), **independent of when the previous
dose was actually taken**. Even if a dose is logged late, the schedule
resets to the next fixed slot the next day.

### Rolling Interval Schedule (`INTERVAL`)

For patterns like "every 8 hours." Anchored to the actual time of the
**previous dose**, not the wall clock (e.g. 06:10 → 14:10 → 22:10). If a
dose is taken late, the whole day's remaining chain shifts accordingly.

```python
if freq_type == 'FIXED_TIMES':
    slots = anchor_times_today()
elif freq_type == 'INTERVAL':
    nxt = last_dose_time + interval
    slots = [nxt]
```

- `FIXED_TIMES`: precompute a static daily list of times, regenerated at
  midnight.
- `INTERVAL`: recompute the next single slot right after each dose is
  logged.

## Bottlenecks and Solutions

### 1. Different Clock Logic for Different Schedules

**Problem:** A naive scheduler that just adds a fixed interval breaks one
of the two common prescription styles — twice-daily plans need fixed
anchor times that stay put regardless of when a dose is taken, while
every-8-hour plans need a rolling chain from the last actual dose time.
Using one clock rule for both causes reminders to fire at the wrong time
or bunch together.

**Solution:** Model each prescription with a `frequency_type` flag and
branch the schedule generator accordingly (see code snippet above).

### 2. Time-Zone Changes Shift Reminders

**Problem:** If reminder times are stored only in local time, travel or a
system time-zone change silently shifts every future dose. For example,
a patient in Delhi (UTC+5:30) sets a 9:00 PM dose, then flies to New York
(UTC-4) — a naive app keeps firing at "9:00 PM device time," now 9.5
hours off from the intended dosing gap. This can cause doses to be
logged too close together or dangerously spaced apart.

**Solution:** Anchor every schedule slot to an absolute instant, not a
local clock string.
- Store each slot in UTC (`datetime`, `timezone.utc`); convert to local
  time only for display.
- On app start/resume, detect the device's current time zone and
  re-render (not recompute) reminder times.
- For `INTERVAL` schedules, keep counting from the UTC timestamp of the
  last dose — the interval logic never changes.
- Use `zoneinfo` (or `pytz`) to handle conversions and daylight-saving
  edge cases.

## Weekly Adherence Report

Turns raw dose logs into something a doctor can act on. Report contents:

- **Per-medicine adherence %** — doses taken ÷ doses scheduled, for each
  prescription
- **Missed-dose timeline** — exact times doses were skipped during the
  week
- **Overall weekly score** — single headline % across all medicines
- **Trend vs. previous week** — improving, steady, or declining
  adherence
- **Doctor-ready export** — PDF / text summary attached to the patient
  record

Example — adherence by day for a sample week:

| Day | Adherence % |
|---|---|
| Mon | 100.0 |
| Tue | 100.0 |
| Wed | 50.0 |
| Thu | 100.0 |
| Fri | 50.0 |
| Sat | 100.0 |
| Sun | 100.0 |

## Module Breakdown

Suggested Python file / module structure:

| Module | Responsibility |
|---|---|
| `prescriptions.py` | Add / edit prescriptions; validates dose, frequency & duration input. |
| `scheduler.py` | Generates dose slots for `FIXED_TIMES` and `INTERVAL` schedules; handles time-zone conversion. |
| `reminders.py` | Polls upcoming slots and triggers notifications (CLI print / GUI pop-up / OS notification). |
| `storage.py` | SQLite connection layer — CRUD for prescriptions, schedule slots and dose logs. |
| `reports.py` | Aggregates a week of logs into per-medicine and overall adherence statistics. |
| `app.py` / `main.py` | Entry point tying modules together; CLI menu or Tkinter GUI event loop. |

## Getting Started

```bash
git clone https://github.com/<your-username>/medication-reminder.git
cd medication-reminder
pip install -r requirements.txt
python main.py
```

> Update the clone URL, entry-point filename, and `requirements.txt`
> contents to match your actual implementation once the code for each
> module above is written.

## Future Scope

- **Native mobile push notifications** — move from desktop pop-ups to
  real Android/iOS push alerts.
- **Doctor-side web dashboard** — let doctors log in and view multiple
  patients' adherence remotely.
- **Predictive risk flags** — use adherence history to flag patients at
  risk of non-compliance.
- **Multi-caregiver alerts** — notify a family member if a critical dose
  is missed.

## License

This project is provided as-is for educational purposes.
