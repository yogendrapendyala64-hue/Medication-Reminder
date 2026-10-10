PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('doctor', 'patient')),
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS patients (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER UNIQUE REFERENCES users (id) ON DELETE SET NULL,
    doctor_id  INTEGER REFERENCES users (id) ON DELETE SET NULL,
    name       TEXT NOT NULL,
    email      TEXT NOT NULL UNIQUE,
    phone      TEXT DEFAULT '',
    dob        TEXT DEFAULT '',
    condition  TEXT DEFAULT 'Not set',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS prescriptions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id    INTEGER NOT NULL REFERENCES patients (id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    dosage        TEXT NOT NULL,
    reminder_time TEXT NOT NULL DEFAULT '08:00',
    start_date    TEXT NOT NULL,
    end_date      TEXT DEFAULT '',
    instructions  TEXT DEFAULT '',
    frequency     TEXT NOT NULL DEFAULT 'Once daily',
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS dose_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    prescription_id INTEGER NOT NULL REFERENCES prescriptions (id) ON DELETE CASCADE,
    log_date        TEXT NOT NULL,
    status          TEXT NOT NULL CHECK (status IN ('taken', 'missed')),
    logged_at       TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (prescription_id, log_date)
);

CREATE TABLE IF NOT EXISTS reminder_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    prescription_id INTEGER NOT NULL REFERENCES prescriptions (id) ON DELETE CASCADE,
    sent_on         TEXT NOT NULL,
    channel         TEXT NOT NULL,
    UNIQUE (prescription_id, sent_on)
);

CREATE INDEX IF NOT EXISTS idx_rx_patient ON prescriptions (patient_id);
CREATE INDEX IF NOT EXISTS idx_logs_date ON dose_logs (log_date);
