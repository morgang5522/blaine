import os
import json
import sqlite3
import logging
from typing import Dict, List, Any, Optional
from src.config import settings

logger = logging.getLogger("blaine.memory")

class SQLiteMemoryManager:
    """
    Persistent Memory Manager backed by SQLite.
    Handles short-term chat history, long-term user facts/preferences, and job records.
    """
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = os.path.abspath(db_path or settings.SQLITE_DB_PATH)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initializes SQLite tables if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Table for short-term chat history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Table for long-term user facts & preferences
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    fact_key TEXT NOT NULL,
                    fact_value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, fact_key, fact_value) ON CONFLICT IGNORE
                );
            """)

            # Table for job history tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_history (
                    job_id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    url TEXT NOT NULL,
                    category TEXT,
                    status TEXT NOT NULL,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Table for scheduled reminders
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    reminder_text TEXT NOT NULL,
                    trigger_at TIMESTAMP NOT NULL,
                    status TEXT DEFAULT 'PENDING',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Table for user to-do & shopping lists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_lists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    list_name TEXT NOT NULL,
                    item_text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            conn.commit()
            logger.info(f"Initialized SQLite memory database at: {self.db_path}")

    def add_reminder(self, user_id: int, chat_id: int, reminder_text: str, trigger_at_iso: str) -> Optional[int]:
        clean_text = reminder_text.strip()
        with self._get_connection() as conn:
            # Prevent duplicate pending reminder for the same user & text
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


    def get_pending_reminders(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, user_id, chat_id, reminder_text, trigger_at FROM reminders WHERE status = 'PENDING' AND trigger_at <= datetime('now')"
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_active_reminders(self, user_id: int) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, user_id, chat_id, reminder_text, trigger_at, created_at FROM reminders WHERE user_id = ? AND status = 'PENDING' ORDER BY trigger_at ASC",
                (user_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def cancel_reminder(
        self,
        user_id: int,
        reminder_id: Optional[int] = None,
        reminder_text: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
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

    def amend_reminder(
        self,
        user_id: int,
        reminder_id: Optional[int] = None,
        reminder_text: Optional[str] = None,
        new_reminder_text: Optional[str] = None,
        new_trigger_at_iso: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
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

    def mark_reminder_triggered(self, reminder_id: int):
        with self._get_connection() as conn:
            conn.execute("UPDATE reminders SET status = 'TRIGGERED' WHERE id = ?", (reminder_id,))
            conn.commit()

    # --- User Lists Management ---
    def add_list_item(self, user_id: int, list_name: str, item_text: str):
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO user_lists (user_id, list_name, item_text) VALUES (?, ?, ?)",
                (user_id, list_name.lower().strip(), item_text.strip())
            )
            conn.commit()

    def get_list_items(self, user_id: int, list_name: str) -> List[str]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT item_text FROM user_lists WHERE user_id = ? AND list_name = ? ORDER BY id ASC",
                (user_id, list_name.lower().strip())
            )
            return [row["item_text"] for row in cursor.fetchall()]

    def remove_list_item(self, user_id: int, list_name: str, item_text: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM user_lists WHERE user_id = ? AND list_name = ? AND LOWER(item_text) = LOWER(?)",
                (user_id, list_name.lower().strip(), item_text.strip())
            )
            conn.commit()
            return cursor.rowcount > 0

    def clear_list(self, user_id: int, list_name: str):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM user_lists WHERE user_id = ? AND list_name = ?", (user_id, list_name.lower().strip()))
            conn.commit()


    # --- Short-Term Conversational Memory ---
    def add_chat_message(self, user_id: int, role: str, content: str):
        """Adds a chat message ('user' or 'model') to SQLite database."""
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO chat_messages (user_id, role, content) VALUES (?, ?, ?)",
                (user_id, role, content)
            )
            conn.commit()

    def get_chat_history(self, user_id: int, limit: int = 20) -> List[Dict[str, str]]:
        """Retrieves recent chat history for a given user."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT role, content FROM (
                    SELECT role, content, id FROM chat_messages 
                    WHERE user_id = ? 
                    ORDER BY id DESC LIMIT ?
                ) ORDER BY id ASC
                """,
                (user_id, limit)
            )
            return [{"role": row["role"], "content": row["content"]} for row in cursor.fetchall()]

    def clear_chat_history(self, user_id: int):
        """Clears conversational history for a user."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
            conn.commit()

    # --- Long-Term Persistent Memory ---
    def store_fact(self, user_id: int, fact_key: str, fact_value: Any) -> bool:
        """Stores an individual persistent user fact into SQLite, preventing duplicate entries."""
        val_str = json.dumps(fact_value) if isinstance(fact_value, (dict, list)) else str(fact_value)
        val_clean = val_str.strip()
        val_lower = val_clean.lower()

        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, fact_value FROM user_facts WHERE user_id = ?",
                (user_id,)
            )
            existing_rows = cursor.fetchall()

            for row in existing_rows:
                existing_val = str(row["fact_value"]).strip().lower()
                # 1. Exact match or new fact is already covered by an existing fact
                if existing_val == val_lower or val_lower in existing_val:
                    logger.info(f"Duplicate fact detected for user [{user_id}]. Skipping: '{val_clean}'")
                    return False
                # 2. Existing fact is a subset of the new, more detailed fact -> update existing
                elif existing_val in val_lower and len(val_lower) > len(existing_val):
                    conn.execute(
                        "UPDATE user_facts SET fact_value = ? WHERE id = ?",
                        (val_clean, row["id"])
                    )
                    conn.commit()
                    logger.info(f"Updated existing fact [{row['id']}] for user [{user_id}]: '{val_clean}'")
                    return True

            # 3. New individual fact -> insert clean record
            conn.execute(
                "INSERT INTO user_facts (user_id, fact_key, fact_value) VALUES (?, ?, ?)",
                (user_id, fact_key, val_clean)
            )
            conn.commit()
            logger.info(f"Saved individual SQLite fact for user [{user_id}]: {fact_key} = {val_clean}")
            return True


    def get_user_facts(self, user_id: int) -> List[Dict[str, Any]]:
        """Retrieves raw stored user facts for a given user."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, fact_key, fact_value, created_at FROM user_facts WHERE user_id = ?",
                (user_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def delete_fact(
        self,
        user_id: int,
        fact_id: Optional[int] = None,
        fact_query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Deletes specific stored user facts by ID or keyword query."""
        with self._get_connection() as conn:
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

    def update_fact(
        self,
        user_id: int,
        new_fact_value: str,
        fact_id: Optional[int] = None,
        fact_query: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Updates an existing stored user fact by ID or matching keyword query."""
        clean_new = new_fact_value.strip()
        with self._get_connection() as conn:
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

    def clear_all_facts(self, user_id: int) -> int:
        """Clears all persistent user facts stored for a user."""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM user_facts WHERE user_id = ?", (user_id,))
            conn.commit()
            return cursor.rowcount

    def get_user_facts_summary(self, user_id: int) -> str:
        """Retrieves formatted summary of stored facts & style preferences for system prompt context."""
        with self._get_connection() as conn:
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

    # --- Job History Tracking ---
    def record_job(self, job_id: str, user_id: int, url: str, category: str, status: str, details: Optional[Dict[str, Any]] = None):
        details_str = json.dumps(details) if details else "{}"
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO job_history (job_id, user_id, url, category, status, details, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (job_id, user_id, url, category, status, details_str)
            )
            conn.commit()

memory_manager = SQLiteMemoryManager()
