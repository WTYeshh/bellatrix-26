import sqlite3
import json
import os
from typing import Dict, Any, List, Optional

class LocalCollectorStorage:
    def __init__(self, db_path: str = "collector_local.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            # 1. Raw telemetry vault: Retains raw data locally by default
            conn.execute("""
                CREATE TABLE IF NOT EXISTS raw_telemetry_vault (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payload_id TEXT UNIQUE NOT NULL,
                    timestamp_utc TEXT NOT NULL,
                    raw_data_json TEXT NOT NULL
                )
            """)

            # 2. Outbox buffer: Holds approved metadata when SaaS is unreachable
            conn.execute("""
                CREATE TABLE IF NOT EXISTS egress_outbox (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payload_id TEXT UNIQUE NOT NULL,
                    payload_json TEXT NOT NULL,
                    attempts INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)

            # 3. Local egress proof archive
            conn.execute("""
                CREATE TABLE IF NOT EXISTS egress_proof_local (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payload_id TEXT UNIQUE NOT NULL,
                    payload_hash TEXT NOT NULL,
                    approved_fields TEXT NOT NULL,
                    redacted_fields TEXT NOT NULL,
                    status TEXT NOT NULL,
                    timestamp_utc TEXT NOT NULL
                )
            """)
            conn.commit()

    def save_raw_telemetry(self, payload_id: str, timestamp_utc: str, raw_data: Dict[str, Any]):
        """Persists raw telemetry strictly inside customer local environment."""
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO raw_telemetry_vault (payload_id, timestamp_utc, raw_data_json) VALUES (?, ?, ?)",
                (payload_id, timestamp_utc, json.dumps(raw_data))
            )
            conn.commit()

    def enqueue_outbox(self, payload_id: str, payload_data: Dict[str, Any], timestamp_utc: str):
        """Buffers approved metadata for delivery."""
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO egress_outbox (payload_id, payload_json, attempts, created_at) VALUES (?, ?, 0, ?)",
                (payload_id, json.dumps(payload_data), timestamp_utc)
            )
            conn.commit()

    def get_pending_outbox(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves buffered metadata payloads awaiting transmission."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, payload_id, payload_json, attempts FROM egress_outbox ORDER BY id ASC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            return [
                {
                    "row_id": r["id"],
                    "payload_id": r["payload_id"],
                    "payload": json.loads(r["payload_json"]),
                    "attempts": r["attempts"]
                }
                for r in rows
            ]

    def remove_from_outbox(self, payload_id: str):
        """Acknowledges delivery and removes payload from buffer."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM egress_outbox WHERE payload_id = ?", (payload_id,))
            conn.commit()

    def increment_attempts(self, payload_id: str):
        with self._get_connection() as conn:
            conn.execute("UPDATE egress_outbox SET attempts = attempts + 1 WHERE payload_id = ?", (payload_id,))
            conn.commit()

    def count_pending(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT count(*) as cnt FROM egress_outbox")
            return cursor.fetchone()["cnt"]

    def record_proof(self, proof: Dict[str, Any], status: str):
        with self._get_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO egress_proof_local 
                   (payload_id, payload_hash, approved_fields, redacted_fields, status, timestamp_utc)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    proof["payload_id"],
                    proof["payload_hash"],
                    json.dumps(proof["approved_fields"]),
                    json.dumps(proof["redacted_fields"]),
                    status,
                    proof["timestamp_utc"]
                )
            )
            conn.commit()

    def get_recent_proofs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT payload_id, payload_hash, approved_fields, redacted_fields, status, timestamp_utc FROM egress_proof_local ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            return [dict(r) for r in cursor.fetchall()]
