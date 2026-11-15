import sqlite3
from pathlib import Path


PROJECT_FOLDER = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_FOLDER / "student_progress.db"


def get_connection():
    return sqlite3.connect(DATABASE_PATH)


def initialize_database():
    """Create the activity table if it does not exist."""

    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student TEXT NOT NULL,
                subject TEXT NOT NULL,
                activity_type TEXT NOT NULL,
                question TEXT NOT NULL,
                score REAL,
                sources TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def save_activity(
    student,
    subject,
    activity_type,
    question,
    score=None,
    sources=""
):
    """Save a student activity."""

    initialize_database()

    with get_connection() as connection:
        connection.execute("""
            INSERT INTO activity (
                student,
                subject,
                activity_type,
                question,
                score,
                sources
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            student,
            subject,
            activity_type,
            question,
            score,
            sources
        ))


def get_all_activity():
    """Return saved activities for the teacher dashboard."""

    initialize_database()

    with get_connection() as connection:
        cursor = connection.execute("""
            SELECT
                student,
                subject,
                activity_type,
                question,
                score,
                sources,
                created_at
            FROM activity
            ORDER BY created_at DESC
        """)

        rows = cursor.fetchall()

    return rows