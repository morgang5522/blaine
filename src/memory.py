from typing import Optional, Dict, List, Any
import datetime

from src.db.context import AppDbContext
from src.utils.timezone import COMMON_TZ_ABBR, parse_timezone_str

class SQLiteMemoryManagerFacade:
    """
    Persistent Memory Manager backed by SQLite.
    This class acts as a backwards-compatible Facade over the new AppDbContext.
    """
    def __init__(self, db_path: Optional[str] = None):
        self._context = AppDbContext(db_path)

    def add_reminder(self, user_id: int, chat_id: int, reminder_text: str, trigger_at_iso: str) -> Optional[int]:
        return self._context.reminders.add(user_id, chat_id, reminder_text, trigger_at_iso)

    def get_pending_reminders(self) -> List[Dict[str, Any]]:
        return self._context.reminders.get_pending()

    def get_active_reminders(self, user_id: int) -> List[Dict[str, Any]]:
        return self._context.reminders.get_active(user_id)

    def cancel_reminder(
        self,
        user_id: int,
        reminder_id: Optional[int] = None,
        reminder_text: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        return self._context.reminders.cancel(user_id, reminder_id, reminder_text)

    def amend_reminder(
        self,
        user_id: int,
        reminder_id: Optional[int] = None,
        reminder_text: Optional[str] = None,
        new_reminder_text: Optional[str] = None,
        new_trigger_at_iso: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        return self._context.reminders.amend(user_id, reminder_id, reminder_text, new_reminder_text, new_trigger_at_iso)

    def mark_reminder_triggered(self, reminder_id: int):
        self._context.reminders.mark_triggered(reminder_id)

    # --- User Lists Management ---
    def add_list_item(self, user_id: int, list_name: str, item_text: str):
        self._context.lists.add_item(user_id, list_name, item_text)

    def get_list_items(self, user_id: int, list_name: str) -> List[str]:
        return self._context.lists.get_items(user_id, list_name)

    def remove_list_item(self, user_id: int, list_name: str, item_text: str) -> bool:
        return self._context.lists.remove_item(user_id, list_name, item_text)

    def clear_list(self, user_id: int, list_name: str):
        self._context.lists.clear(user_id, list_name)

    # --- Short-Term Conversational Memory ---
    def add_chat_message(self, user_id: int, role: str, content: str):
        self._context.chat.add_message(user_id, role, content)

    def get_chat_history(self, user_id: int, limit: int = 20) -> List[Dict[str, str]]:
        return self._context.chat.get_history(user_id, limit)

    def clear_chat_history(self, user_id: int):
        self._context.chat.clear_history(user_id)

    # --- Long-Term Persistent Memory ---
    def store_fact(self, user_id: int, fact_key: str, fact_value: Any) -> bool:
        return self._context.facts.store(user_id, fact_key, fact_value)

    def get_user_facts(self, user_id: int) -> List[Dict[str, Any]]:
        return self._context.facts.get_by_user(user_id)

    def delete_fact(
        self,
        user_id: int,
        fact_id: Optional[int] = None,
        fact_query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        return self._context.facts.delete(user_id, fact_id, fact_query)

    def update_fact(
        self,
        user_id: int,
        new_fact_value: str,
        fact_id: Optional[int] = None,
        fact_query: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        return self._context.facts.update(user_id, new_fact_value, fact_id, fact_query)

    def clear_all_facts(self, user_id: int) -> int:
        return self._context.facts.clear_all(user_id)

    def get_user_timezone(self, user_id: int) -> Optional[tuple[datetime.tzinfo, str]]:
        return self._context.facts.get_user_timezone(user_id)

    def get_user_facts_summary(self, user_id: int) -> str:
        return self._context.facts.get_user_facts_summary(user_id)

    # --- Job History Tracking ---
    def record_job(self, job_id: str, user_id: int, url: str, category: str, status: str, details: Optional[Dict[str, Any]] = None):
        self._context.jobs.record(job_id, user_id, url, category, status, details)

# Singleton Facade Instance (preserves backwards compatibility)
memory_manager = SQLiteMemoryManagerFacade()

# Keep timezone imports around just in case someone imported them from here
COMMON_TZ_ABBR = COMMON_TZ_ABBR
parse_timezone_str = parse_timezone_str
