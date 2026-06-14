# This file has been created with the assistance of an AI tool.
import sqlite3
import time


class State:
    def __init__(self, db_path: str):
        self._db_path = db_path
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_events (
                    event_id TEXT PRIMARY KEY,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS state (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

    def is_processed(self, event_id: str) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM processed_events WHERE event_id = ?", (event_id,)
            ).fetchone()
            return row is not None

    def mark_processed(self, event_id: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO processed_events (event_id) VALUES (?)",
                (event_id,)
            )

    def get_last_event_created(self) -> int:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT value FROM state WHERE key = 'last_event_created'"
            ).fetchone()
            if row is None:
                return int(time.time()) - 86400
            return int(row[0])

    def set_last_event_created(self, timestamp: int) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO state (key, value) VALUES ('last_event_created', ?)",
                (str(timestamp),)
            )
