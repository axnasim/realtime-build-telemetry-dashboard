import sqlite3
from typing import Tuple, List, Dict, Any

class Store:
    def __init__(self, path: str = ":memory:"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS events ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "agent_id TEXT, build_id TEXT, status TEXT, duration_ms INTEGER, ts REAL)"
        )
        self.conn.commit()

    def insert_event(self, agent_id: str, build_id: str, status: str, duration_ms: int, ts: float) -> None:
        self.conn.execute(
            "INSERT INTO events (agent_id, build_id, status, duration_ms, ts) VALUES (?, ?, ?, ?, ?)",
            (agent_id, build_id, status, duration_ms, ts)
        )
        self.conn.commit()

    def summary(self) -> Dict[str, Any]:
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*), SUM(CASE WHEN status='PASS' THEN 1 ELSE 0 END), SUM(CASE WHEN status='FAIL' THEN 1 ELSE 0 END), AVG(duration_ms) FROM events")
        total, passed, failed, avg = cur.fetchone()
        return {
            "total": int(total or 0),
            "passed": int(passed or 0),
            "failed": int(failed or 0),
            "avg_duration_ms": float(avg or 0.0)
        }
