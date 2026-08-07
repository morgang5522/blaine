import json
from typing import Optional, Dict, Any
from src.db.core import DatabaseManager

class JobsRepository:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def record(self, job_id: str, user_id: int, url: str, category: str, status: str, details: Optional[Dict[str, Any]] = None):
        details_str = json.dumps(details) if details else "{}"
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO job_history (job_id, user_id, url, category, status, details, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (job_id, user_id, url, category, status, details_str)
            )
            conn.commit()
