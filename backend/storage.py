from __future__ import annotations

import hashlib
import os
import sqlite3
from datetime import datetime, timezone


def _db_path() -> str:
    base = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "til.sqlite3")


def init_db() -> None:
    conn = sqlite3.connect(_db_path())
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                code_hash TEXT NOT NULL,
                input_text TEXT,
                output_text TEXT,
                error_text TEXT,
                status TEXT NOT NULL
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def save_run(code: str, input_text: str | None, output_text: str, error_text: str | None, status: str) -> None:
    h = hashlib.sha256(code.encode("utf-8")).hexdigest()
    created = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(_db_path())
    try:
        conn.execute(
            """
            INSERT INTO runs (created_at, code_hash, input_text, output_text, error_text, status)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (created, h, input_text, output_text, error_text, status),
        )
        # keep only recent rows
        conn.execute(
            """
            DELETE FROM runs
            WHERE id NOT IN (SELECT id FROM runs ORDER BY id DESC LIMIT 50);
            """
        )
        conn.commit()
    finally:
        conn.close()


def last_runs(limit: int = 20) -> list[dict]:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, created_at, status, output_text, error_text FROM runs ORDER BY id DESC LIMIT ?;",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

