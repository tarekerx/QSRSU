"""SQLite database layer for QSRSU (no ORM)."""

import os
import sqlite3

DB_PATH: str = os.getenv("DB_PATH", "qsrsu.db")

# Whitelist of columns that may be updated via update_question().
_ALLOWED_FIELDS = {
    "telegram_user_id",
    "image_path",
    "question_text",
    "options",
    "user_answer",
    "correct_answer",
    "explanation",
    "is_correct",
    "created_at",
}


def _connect() -> sqlite3.Connection:
    """Open a connection with Row factory for dict conversion."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the questions table if it doesn't exist."""
    conn = _connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                image_path TEXT NOT NULL,
                question_text TEXT,
                options TEXT,
                user_answer TEXT,
                correct_answer TEXT,
                explanation TEXT,
                is_correct INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def create_question(telegram_user_id: int, image_path: str) -> int:
    """Insert a row with only telegram_user_id and image_path; return the new id."""
    conn = _connect()
    try:
        cursor = conn.execute(
            "INSERT INTO questions (telegram_user_id, image_path) VALUES (?, ?)",
            (telegram_user_id, image_path),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def update_question(question_id: int, **fields) -> None:
    """Update any given fields of a question by id."""
    if not fields:
        return

    for key in fields:
        if key not in _ALLOWED_FIELDS:
            raise ValueError(f"Invalid field: {key}")

    set_clause = ", ".join(f"{key} = ?" for key in fields)
    values = list(fields.values()) + [question_id]

    conn = _connect()
    try:
        conn.execute(
            f"UPDATE questions SET {set_clause} WHERE id = ?",  # noqa: S608
            values,
        )
        conn.commit()
    finally:
        conn.close()


def get_question(question_id: int):
    """Return the full row as a dict, or None if not found."""
    conn = _connect()
    try:
        cursor = conn.execute(
            "SELECT * FROM questions WHERE id = ?",
            (question_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)
    finally:
        conn.close()


def list_questions() -> list:
    """Return all rows as a list of dicts."""
    conn = _connect()
    try:
        cursor = conn.execute("SELECT * FROM questions")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
