from typing import List, Dict
from src.db.core import DatabaseManager

class ChatRepository:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def add_message(self, user_id: int, role: str, content: str):
        with self.db.get_connection() as conn:
            conn.execute(
                "INSERT INTO chat_messages (user_id, role, content) VALUES (?, ?, ?)",
                (user_id, role, content)
            )
            conn.commit()

    def get_history(self, user_id: int, limit: int = 20) -> List[Dict[str, str]]:
        with self.db.get_connection() as conn:
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

    def clear_history(self, user_id: int):
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
            conn.commit()
