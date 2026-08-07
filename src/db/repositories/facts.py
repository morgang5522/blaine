import json
import logging
import re
import datetime
from typing import Dict, List, Any, Optional

from src.db.core import DatabaseManager
from src.utils.timezone import parse_timezone_str

logger = logging.getLogger("blaine.memory.facts")

class FactsRepository:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def store(self, user_id: int, fact_key: str, fact_value: Any) -> bool:
        val_str = json.dumps(fact_value) if isinstance(fact_value, (dict, list)) else str(fact_value)
        val_clean = val_str.strip()
        val_lower = val_clean.lower()

        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, fact_value FROM user_facts WHERE user_id = ?",
                (user_id,)
            )
            existing_rows = cursor.fetchall()

            for row in existing_rows:
                existing_val = str(row["fact_value"]).strip().lower()
                if existing_val == val_lower or val_lower in existing_val:
                    logger.info(f"Duplicate fact detected for user [{user_id}]. Skipping: '{val_clean}'")
                    return False
                elif existing_val in val_lower and len(val_lower) > len(existing_val):
                    conn.execute(
                        "UPDATE user_facts SET fact_value = ? WHERE id = ?",
                        (val_clean, row["id"])
                    )
                    conn.commit()
                    logger.info(f"Updated existing fact [{row['id']}] for user [{user_id}]: '{val_clean}'")
                    return True

            conn.execute(
                "INSERT INTO user_facts (user_id, fact_key, fact_value) VALUES (?, ?, ?)",
                (user_id, fact_key, val_clean)
            )
            conn.commit()
            logger.info(f"Saved individual SQLite fact for user [{user_id}]: {fact_key} = {val_clean}")
            return True

    def get_by_user(self, user_id: int) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, fact_key, fact_value, created_at FROM user_facts WHERE user_id = ?",
                (user_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def delete(self, user_id: int, fact_id: Optional[int] = None, fact_query: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            to_delete = []
            if fact_id is not None:
                cursor = conn.execute(
                    "SELECT id, fact_key, fact_value FROM user_facts WHERE user_id = ? AND id = ?",
                    (user_id, fact_id)
                )
                to_delete = [dict(r) for r in cursor.fetchall()]
            elif fact_query:
                clean_query = fact_query.strip()
                cursor = conn.execute(
                    """
                    SELECT id, fact_key, fact_value FROM user_facts 
                    WHERE user_id = ? AND (LOWER(fact_value) LIKE LOWER(?) OR LOWER(fact_key) LIKE LOWER(?))
                    """,
                    (user_id, f"%{clean_query}%", f"%{clean_query}%")
                )
                to_delete = [dict(r) for r in cursor.fetchall()]

            if not to_delete:
                return []

            del_ids = [r["id"] for r in to_delete]
            placeholders = ",".join(["?"] * len(del_ids))
            conn.execute(
                f"DELETE FROM user_facts WHERE id IN ({placeholders})",
                del_ids
            )
            conn.commit()
            return to_delete

    def update(self, user_id: int, new_fact_value: str, fact_id: Optional[int] = None, fact_query: Optional[str] = None) -> Optional[Dict[str, Any]]:
        clean_new = new_fact_value.strip()
        with self.db.get_connection() as conn:
            target = None
            if fact_id is not None:
                cursor = conn.execute(
                    "SELECT id, fact_key, fact_value FROM user_facts WHERE user_id = ? AND id = ?",
                    (user_id, fact_id)
                )
                target = cursor.fetchone()

            if not target and fact_query:
                clean_q = fact_query.strip()
                cursor = conn.execute(
                    """
                    SELECT id, fact_key, fact_value FROM user_facts 
                    WHERE user_id = ? AND (LOWER(fact_value) LIKE LOWER(?) OR LOWER(fact_key) LIKE LOWER(?))
                    """,
                    (user_id, f"%{clean_q}%", f"%{clean_q}%")
                )
                target = cursor.fetchone()

            if not target:
                return None

            t_id = target["id"]
            conn.execute(
                "UPDATE user_facts SET fact_value = ? WHERE id = ?",
                (clean_new, t_id)
            )
            conn.commit()

            cursor = conn.execute(
                "SELECT id, fact_key, fact_value, created_at FROM user_facts WHERE id = ?",
                (t_id,)
            )
            res = cursor.fetchone()
            return dict(res) if res else None

    def clear_all(self, user_id: int) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.execute("DELETE FROM user_facts WHERE user_id = ?", (user_id,))
            conn.commit()
            return cursor.rowcount

    def get_user_timezone(self, user_id: int) -> Optional[tuple[datetime.tzinfo, str]]:
        facts = self.get_by_user(user_id)
        if not facts:
            return None

        tz_facts = [
            f for f in facts
            if any(k in f["fact_key"].lower() or k in f["fact_value"].lower() for k in ["timezone", "time zone", "tz"])
        ]

        search_list = tz_facts if tz_facts else facts

        for fact in search_list:
            val = fact["fact_value"]
            res = parse_timezone_str(val)
            if res:
                return res

            tokens = re.split(r'[\s,;:="]+', val)
            for token in tokens:
                token_clean = token.strip()
                if token_clean.lower() in ("timezone", "time", "zone", "tz", "is", "user's", "my", "the", "fact"):
                    continue
                res = parse_timezone_str(token_clean)
                if res:
                    return res

        return None

    def get_user_facts_summary(self, user_id: int) -> str:
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT fact_key, fact_value FROM user_facts WHERE user_id = ?",
                (user_id,)
            )
            rows = cursor.fetchall()

        if not rows:
            return "No prior saved preferences."

        style_facts = []
        general_facts = []
        style_keywords = {"name", "nickname", "tone", "style", "communication", "humor", "language", "brevity", "concise", "formality", "speak", "voice"}

        for row in rows:
            key = row['fact_key']
            val = row['fact_value']
            if any(k in key.lower() or k in val.lower() for k in style_keywords):
                style_facts.append(f"• {key}: {val}")
            else:
                general_facts.append(f"• {key}: {val}")

        summary_parts = []
        if style_facts:
            summary_parts.append("Speaking Style & Communication Preferences:\n" + "\n".join(style_facts))
        if general_facts:
            summary_parts.append("General User Context & Facts:\n" + "\n".join(general_facts))

        return "\n\n".join(summary_parts)
