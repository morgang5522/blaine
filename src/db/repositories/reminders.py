import logging
from typing import Dict, List, Any, Optional
from src.db.core import DatabaseManager

logger = logging.getLogger("blaine.memory.reminders")

class RemindersRepository:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def add(self, user_id: int, chat_id: int, reminder_text: str, trigger_at_iso: str) -> Optional[int]:
        clean_text = reminder_text.strip()
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT id FROM reminders WHERE user_id = ? AND LOWER(reminder_text) = LOWER(?) AND status = 'PENDING'",
                (user_id, clean_text)
            )
            row = cursor.fetchone()
            if row:
                logger.info(f"Active reminder already exists for user {user_id} with text '{clean_text}'. Skipping duplicate.")
                return None

            cursor = conn.execute(
                "INSERT INTO reminders (user_id, chat_id, reminder_text, trigger_at) VALUES (?, ?, ?, ?)",
                (user_id, chat_id, clean_text, trigger_at_iso)
            )
            conn.commit()
            return cursor.lastrowid

    def get_pending(self) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, user_id, chat_id, reminder_text, trigger_at FROM reminders WHERE status = 'PENDING' AND trigger_at <= datetime('now')"
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_active(self, user_id: int) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, user_id, chat_id, reminder_text, trigger_at, created_at FROM reminders WHERE user_id = ? AND status = 'PENDING' ORDER BY trigger_at ASC",
                (user_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def cancel(self, user_id: int, reminder_id: Optional[int] = None, reminder_text: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            to_cancel = []
            if reminder_id is not None:
                cursor = conn.execute(
                    "SELECT id, reminder_text, trigger_at FROM reminders WHERE user_id = ? AND id = ? AND status = 'PENDING'",
                    (user_id, reminder_id)
                )
                to_cancel = [dict(r) for r in cursor.fetchall()]
            elif reminder_text:
                clean_text = reminder_text.strip()
                cursor = conn.execute(
                    "SELECT id, reminder_text, trigger_at FROM reminders WHERE user_id = ? AND LOWER(reminder_text) LIKE LOWER(?) AND status = 'PENDING'",
                    (user_id, f"%{clean_text}%")
                )
                to_cancel = [dict(r) for r in cursor.fetchall()]

            if not to_cancel:
                return []

            cancel_ids = [r["id"] for r in to_cancel]
            placeholders = ",".join(["?"] * len(cancel_ids))
            conn.execute(
                f"UPDATE reminders SET status = 'CANCELLED' WHERE id IN ({placeholders})",
                cancel_ids
            )
            conn.commit()
            return to_cancel

    def amend(
        self,
        user_id: int,
        reminder_id: Optional[int] = None,
        reminder_text: Optional[str] = None,
        new_reminder_text: Optional[str] = None,
        new_trigger_at_iso: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            target = None
            if reminder_id is not None:
                cursor = conn.execute(
                    "SELECT id, reminder_text, trigger_at FROM reminders WHERE user_id = ? AND id = ? AND status = 'PENDING'",
                    (user_id, reminder_id)
                )
                target = cursor.fetchone()

            if not target and reminder_text:
                clean_text = reminder_text.strip()
                cursor = conn.execute(
                    "SELECT id, reminder_text, trigger_at FROM reminders WHERE user_id = ? AND LOWER(reminder_text) LIKE LOWER(?) AND status = 'PENDING'",
                    (user_id, f"%{clean_text}%")
                )
                target = cursor.fetchone()

            if not target:
                return None

            t_id = target["id"]
            updated_text = new_reminder_text.strip() if new_reminder_text else target["reminder_text"]
            updated_trigger = new_trigger_at_iso if new_trigger_at_iso else target["trigger_at"]

            conn.execute(
                "UPDATE reminders SET reminder_text = ?, trigger_at = ? WHERE id = ?",
                (updated_text, updated_trigger, t_id)
            )
            conn.commit()

            cursor = conn.execute(
                "SELECT id, user_id, chat_id, reminder_text, trigger_at, created_at FROM reminders WHERE id = ?",
                (t_id,)
            )
            res = cursor.fetchone()
            return dict(res) if res else None

    def mark_triggered(self, reminder_id: int):
        with self.db.get_connection() as conn:
            conn.execute("UPDATE reminders SET status = 'TRIGGERED' WHERE id = ?", (reminder_id,))
            conn.commit()
