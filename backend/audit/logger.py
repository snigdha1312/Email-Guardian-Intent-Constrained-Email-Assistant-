import os
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from policy_engine import PolicyDecision

DB_PATH = os.path.join(os.path.dirname(__file__), "audit.db")

class AuditLogger:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DB_PATH
        self._init_db()

    def _init_db(self):
        """Creates the audit log table if it doesn't already exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                identity TEXT NOT NULL,
                action TEXT NOT NULL,
                params TEXT NOT NULL,
                decision TEXT NOT NULL,
                reason TEXT NOT NULL,
                rule_matched TEXT
            )
        """)
        conn.commit()
        conn.close()

    def log(self, decision: PolicyDecision, identity: str, action: str, params: dict) -> None:
        """
        Logs a policy evaluation decision.
        Must be called for every policy evaluation (both allows and blocks).
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        from datetime import timezone
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        decision_str = "allow" if decision.allowed else "block"
        params_json = json.dumps(params)
        
        cursor.execute("""
            INSERT INTO audit_logs (timestamp, identity, action, params, decision, reason, rule_matched)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (timestamp, identity, action, params_json, decision_str, decision.reason, decision.rule_matched))
        
        conn.commit()
        conn.close()

    def get_trail(self, identity: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Returns the audit trail, most recent first.
        Optionally filtered by identity.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if identity:
            cursor.execute("""
                SELECT id, timestamp, identity, action, params, decision, reason, rule_matched
                FROM audit_logs
                WHERE identity = ?
                ORDER BY timestamp DESC, id DESC
                LIMIT ?
            """, (identity, limit))
        else:
            cursor.execute("""
                SELECT id, timestamp, identity, action, params, decision, reason, rule_matched
                FROM audit_logs
                ORDER BY timestamp DESC, id DESC
                LIMIT ?
            """, (limit,))
            
        rows = cursor.fetchall()
        result = []
        for row in rows:
            result.append({
                "id": row["id"],
                "timestamp": row["timestamp"],
                "identity": row["identity"],
                "action": row["action"],
                "params": json.loads(row["params"]),
                "decision": row["decision"],
                "reason": row["reason"],
                "rule_matched": row["rule_matched"]
            })
            
        conn.close()
        return result
