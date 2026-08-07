from typing import Optional
from src.db.core import DatabaseManager
from src.db.repositories.chat import ChatRepository
from src.db.repositories.facts import FactsRepository
from src.db.repositories.reminders import RemindersRepository
from src.db.repositories.lists import ListsRepository
from src.db.repositories.jobs import JobsRepository

class AppDbContext:
    """
    Entity Framework style DbContext that holds all the repositories.
    """
    def __init__(self, db_path: Optional[str] = None):
        self.db = DatabaseManager(db_path)
        self.chat = ChatRepository(self.db)
        self.facts = FactsRepository(self.db)
        self.reminders = RemindersRepository(self.db)
        self.lists = ListsRepository(self.db)
        self.jobs = JobsRepository(self.db)
