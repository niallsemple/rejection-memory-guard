import os
import sqlite3
import json
from typing import List, Optional, Any
from datetime import datetime, timezone

from rmg.models import Record, Status, RecordType


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Ledger:
    def __init__(self, path: Optional[str] = None):
        if path is None:
            path = os.environ.get("RMG_DB", os.path.join("~", ".rmg", "ledger.db"))
        
        self.path = path
        
        if self.path != ":memory:":
            dir_name = os.path.dirname(self.path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
        
        self.conn = sqlite3.connect(self.path)
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS records (
                id TEXT PRIMARY KEY,
                record_type TEXT,
                status TEXT,
                data TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                at TEXT,
                kind TEXT,
                record_id TEXT,
                payload TEXT
            )
        """)
        self.conn.commit()

    def add(self, record: Record) -> Record:
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO records (id, record_type, status, data) VALUES (?, ?, ?, ?)",
            (record.id, record.record_type.value, record.status.value, record.to_json())
        )
        self.conn.commit()
        return record

    def get(self, id: str) -> Optional[Record]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT data FROM records WHERE id = ?", (id,))
        row = cursor.fetchone()
        if row:
            return Record.from_json(row[0])
        return None

    def update(self, record: Record):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE records SET record_type = ?, status = ?, data = ? WHERE id = ?",
            (record.record_type.value, record.status.value, record.to_json(), record.id)
        )
        self.conn.commit()

    def all(self, record_type: Optional[RecordType] = None, statuses: Optional[List[Status]] = None) -> List[Record]:
        cursor = self.conn.cursor()
        query = "SELECT data FROM records"
        params = []
        
        conditions = []
        if record_type:
            conditions.append("record_type = ?")
            params.append(record_type.value)
        if statuses:
            placeholders = ",".join(["?"] * len(statuses))
            conditions.append(f"status IN ({placeholders})")
            params.extend([s.value for s in statuses])
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [Record.from_json(row[0]) for row in rows]

    def active(self) -> List[Record]:
        return self.all(
            record_type=RecordType.REJECTION,
            statuses=[Status.ACTIVE, Status.REOPENED]
        )

    def set_status(self, id: str, status: Status, reason: str):
        record = self.get(id)
        if record:
            record.set_status(status, reason)
            self.update(record)

    def increment_reproposal(self, id: str):
        record = self.get(id)
        if record:
            record.times_reproposed += 1
            record.last_reproposal = _now_iso()
            self.update(record)

    def log_event(self, kind: str, record_id: Optional[str] = None, payload: Optional[dict] = None):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO events (at, kind, record_id, payload) VALUES (?, ?, ?, ?)",
            (_now_iso(), kind, record_id, json.dumps(payload) if payload else None)
        )
        self.conn.commit()

    def events(self, kind: Optional[str] = None) -> List[dict]:
        cursor = self.conn.cursor()
        if kind:
            cursor.execute(
                "SELECT at, kind, record_id, payload FROM events WHERE kind = ?",
                (kind,)
            )
        else:
            cursor.execute("SELECT at, kind, record_id, payload FROM events")
        
        rows = cursor.fetchall()
        results = []
        for row in rows:
            results.append({
                "at": row[0],
                "kind": row[1],
                "record_id": row[2],
                "payload": json.loads(row[3]) if row[3] else None
            })
        return results

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
