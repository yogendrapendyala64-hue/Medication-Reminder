CREATE DATABASE IF NOT EXISTS medication_reminder
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE medication_reminder;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(190) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('doctor', 'patient') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prescriptions (
    id INT AUTO_INCREMENT PRIMARY KEY,

    doctor_id INT NOT NULL,
    patient_id INT NOT NULL,

    medicine_name VARCHAR(150) NOT NULL,
    dose VARCHAR(100) NOT NULL,

    frequency_type ENUM(
        'fixed_times',
        'interval'
    ) NOT NULL DEFAULT 'fixed_times',

    fixed_times VARCHAR(255),
    interval_hours INT,

    start_date DATE NOT NULL,
    end_date DATE NOT NULL,

    notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (doctor_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (patient_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dose_slots (
    id INT AUTO_INCREMENT PRIMARY KEY,

    prescription_id INT NOT NULL,

    scheduled_at DATETIME NOT NULL,

    status ENUM(
        'pending',
        'taken',
        'missed'
    ) NOT NULL DEFAULT 'pending',

    taken_at DATETIME NULL,

    UNIQUE KEY unique_dose_slot (
        prescription_id,
        scheduled_at
    ),

    FOREIGN KEY (prescription_id)
        REFERENCES prescriptions(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dose_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,

    dose_slot_id INT NOT NULL,
    patient_id INT NOT NULL,

    status ENUM(
        'taken',
        'missed'
    ) NOT NULL,

    logged_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    notes VARCHAR(255),

    FOREIGN KEY (dose_slot_id)
        REFERENCES dose_slots(id)
        ON DELETE CASCADE,

    FOREIGN KEY (patient_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);