from typing import List
from src.db.core import DatabaseManager

class ListsRepository:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def add_item(self, user_id: int, list_name: str, item_text: str):
        with self.db.get_connection() as conn:
            conn.execute(
                "INSERT INTO user_lists (user_id, list_name, item_text) VALUES (?, ?, ?)",
                (user_id, list_name.lower().strip(), item_text.strip())
            )
            conn.commit()

    def get_items(self, user_id: int, list_name: str) -> List[str]:
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT item_text FROM user_lists WHERE user_id = ? AND list_name = ? ORDER BY id ASC",
                (user_id, list_name.lower().strip())
            )
            return [row["item_text"] for row in cursor.fetchall()]

    def remove_item(self, user_id: int, list_name: str, item_text: str) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM user_lists WHERE user_id = ? AND list_name = ? AND LOWER(item_text) = LOWER(?)",
                (user_id, list_name.lower().strip(), item_text.strip())
            )
            conn.commit()
            return cursor.rowcount > 0

    def clear(self, user_id: int, list_name: str):
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM user_lists WHERE user_id = ? AND list_name = ?", (user_id, list_name.lower().strip()))
            conn.commit()
