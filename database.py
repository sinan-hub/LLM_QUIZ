# /mnt/data/database.py
import sqlite3
import json
from typing import Optional, Dict, Any

class QuizDatabase:
    def __init__(self, path: str = "./quiz_data.db"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self._ensure_tables()

    def _ensure_tables(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS attempts (
                attempt_id TEXT PRIMARY KEY,
                url TEXT,
                secret TEXT,
                status TEXT,
                answers TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def save_attempt(self, attempt_id: str, url: str, secret: str, status: str = "processing"):
        cur = self.conn.cursor()
        cur.execute("INSERT OR REPLACE INTO attempts (attempt_id, url, secret, status, answers) VALUES (?, ?, ?, ?, ?)",
                    (attempt_id, url, secret, status, json.dumps({})))
        self.conn.commit()

    def update_attempt_status(self, attempt_id: str, status: str, answers: Dict[str, Any] = None):
        cur = self.conn.cursor()
        cur.execute("UPDATE attempts SET status=?, answers=? WHERE attempt_id=?",
                    (status, json.dumps(answers or {}), attempt_id))
        self.conn.commit()

    def get_attempt(self, attempt_id: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT attempt_id, url, status, answers, created_at FROM attempts WHERE attempt_id=?", (attempt_id,))
        row = cur.fetchone()
        if not row:
            return None
        return {"attempt_id": row[0], "url": row[1], "status": row[2], "answers": json.loads(row[3]), "created_at": row[4]}

    def close(self):
        self.conn.close()
