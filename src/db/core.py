import os
import sqlite3
import logging
from typing import Optional
from src.config import settings

logger = logging.getLogger("blaine.db")

class DatabaseManager:
    """
    Manages the SQLite database connection and initialization.
    """
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = os.path.abspath(db_path or settings.SQLITE_DB_PATH)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Returns a new SQLite connection with Row factory enabled."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initializes SQLite tables if they do not exist."""
        with self.get_connection() as conn:
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
            logger.info(f"Initialized SQLite database at: {self.db_path}")
