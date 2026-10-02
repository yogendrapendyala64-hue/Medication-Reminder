import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv("DB_NAME", "medication_reminder")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("Yogi@2007", ""),
    "database": DB_NAME,
}


def get_connection(with_database=True):
    config = DB_CONFIG.copy()

    if not with_database:
        config.pop("database", None)

    try:
        return mysql.connector.connect(**config)
    except Error as e:
        raise RuntimeError(f"MySQL connection failed: {e}")


def init_database():
    """
    Database and tables create automatically.
    """

    # Create database
    connection = get_connection(with_database=False)

    try:
        cursor = connection.cursor()

        cursor.execute(
            f"""
            CREATE DATABASE IF NOT EXISTS `{DB_NAME}`
            CHARACTER SET utf8mb4
            COLLATE utf8mb4_unicode_ci
            """
        )

        cursor.close()
        connection.close()

    except Exception:
        try:
            connection.close()
        except Exception:
            pass
        raise

    # Connect to database
    connection = get_connection()

    try:
        cursor = connection.cursor()

        # USERS
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                full_name VARCHAR(120) NOT NULL,
                email VARCHAR(190) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                role ENUM('doctor', 'patient') NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB
            """
        )

        # PRESCRIPTIONS
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS prescriptions (
                id INT AUTO_INCREMENT PRIMARY KEY,

                doctor_id INT NOT NULL,
                patient_id INT NOT NULL,

                medicine_name VARCHAR(150) NOT NULL,
                dose VARCHAR(100) NOT NULL,

                frequency_type ENUM('fixed_times', 'interval')
                    NOT NULL DEFAULT 'fixed_times',

                fixed_times VARCHAR(255) DEFAULT NULL,
                interval_hours INT DEFAULT NULL,

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
            ) ENGINE=InnoDB
            """
        )

        # DOSE SLOTS
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS dose_slots (
                id INT AUTO_INCREMENT PRIMARY KEY,

                prescription_id INT NOT NULL,

                scheduled_at DATETIME NOT NULL,

                status ENUM('pending', 'taken', 'missed')
                    NOT NULL DEFAULT 'pending',

                taken_at DATETIME DEFAULT NULL,

                UNIQUE KEY unique_dose_slot
                    (prescription_id, scheduled_at),

                FOREIGN KEY (prescription_id)
                    REFERENCES prescriptions(id)
                    ON DELETE CASCADE
            ) ENGINE=InnoDB
            """
        )

        # DOSE LOGS
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS dose_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,

                dose_slot_id INT NOT NULL,
                patient_id INT NOT NULL,

                status ENUM('taken', 'missed')
                    NOT NULL,

                logged_at DATETIME DEFAULT CURRENT_TIMESTAMP,

                notes VARCHAR(255),

                FOREIGN KEY (dose_slot_id)
                    REFERENCES dose_slots(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (patient_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            ) ENGINE=InnoDB
            """
        )

        connection.commit()
        cursor.close()

    finally:
        connection.close()


def query(sql, params=None, fetchall=True):
    connection = get_connection()

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(sql, params or ())

        if fetchall:
            result = cursor.fetchall()
        else:
            result = cursor.fetchone()

        cursor.close()

        return result

    finally:
        connection.close()


def execute(sql, params=None):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(sql, params or ())

        connection.commit()

        last_id = cursor.lastrowid

        cursor.close()

        return last_id

    finally:
        connection.close()