import unittest
import asyncio
from src.memory import SQLiteMemoryManager
from src.tools.memory import (
    RememberUserFactTool,
    ForgetMemoryTool,
    UpdateMemoryTool,
    ListMemoriesTool,
    ClearAllMemoriesTool,
    ClearChatHistoryTool
)

class TestMemoryFeatures(unittest.TestCase):
    def setUp(self):
        self.memory_mgr = SQLiteMemoryManager(":memory:")

    def test_sqlite_memory_manager_crud(self):
        user_id = 999

        # 1. Store facts
        self.assertTrue(self.memory_mgr.store_fact(user_id, "fact", "Favorite team is Jaguars"))
        self.assertTrue(self.memory_mgr.store_fact(user_id, "fact", "Loves drinking espresso"))
        self.assertEqual(len(self.memory_mgr.get_user_facts(user_id)), 2)

        # 2. Update fact by query
        updated = self.memory_mgr.update_fact(user_id, "Favorite team is Chiefs", fact_query="Jaguars")
        self.assertIsNotNone(updated)
        self.assertEqual(updated["fact_value"], "Favorite team is Chiefs")

        # 3. Delete fact by query
        deleted = self.memory_mgr.delete_fact(user_id, fact_query="espresso")
        self.assertEqual(len(deleted), 1)
        self.assertEqual(deleted[0]["fact_value"], "Loves drinking espresso")
        self.assertEqual(len(self.memory_mgr.get_user_facts(user_id)), 1)

        # 4. Clear all facts
        cleared_count = self.memory_mgr.clear_all_facts(user_id)
        self.assertEqual(cleared_count, 1)
        self.assertEqual(len(self.memory_mgr.get_user_facts(user_id)), 0)

    def test_memory_tools_execution(self):
        async def run_test():
            user_id = 888

            remember_tool = RememberUserFactTool()
            forget_tool = ForgetMemoryTool()
            update_tool = UpdateMemoryTool()
            list_tool = ListMemoriesTool()
            clear_tool = ClearAllMemoriesTool()
            clear_chat_tool = ClearChatHistoryTool()

            # Mock memory_manager inside tools to use in-memory DB
            with unittest.mock.patch("src.tools.memory.memory_manager", self.memory_mgr):
                # 1. Remember fact
                res = await remember_tool.execute(user_id=user_id, fact="User's favorite color is Navy Blue")
                self.assertEqual(res["status"], "SUCCESS")
                self.assertTrue(res["is_new"])

                # 2. List memories
                res = await list_tool.execute(user_id=user_id)
                self.assertEqual(res["status"], "SUCCESS")
                self.assertEqual(len(res["facts"]), 1)
                self.assertIn("Navy Blue", res["message"])

                # 3. Update memory
                res = await update_tool.execute(user_id=user_id, new_fact="User's favorite color is Emerald Green", fact_query="color")
                self.assertEqual(res["status"], "SUCCESS")
                self.assertIn("Emerald Green", res["message"])

                # 4. Forget memory
                res = await forget_tool.execute(user_id=user_id, fact_query="color")
                self.assertEqual(res["status"], "SUCCESS")
                self.assertEqual(res["deleted_count"], 1)

                # 5. Clear all memories
                await remember_tool.execute(user_id=user_id, fact="Fact 1")
                await remember_tool.execute(user_id=user_id, fact="Fact 2")
                res = await clear_tool.execute(user_id=user_id)
                self.assertEqual(res["status"], "SUCCESS")
                self.assertEqual(res["cleared_count"], 2)

                # 6. Clear chat history tool
                self.memory_mgr.add_chat_message(user_id, "user", "Hello")
                self.memory_mgr.add_chat_message(user_id, "model", "Hi there!")
                self.assertEqual(len(self.memory_mgr.get_chat_history(user_id)), 2)

                res = await clear_chat_tool.execute(user_id=user_id)
                self.assertEqual(res["status"], "SUCCESS")
                self.assertEqual(len(self.memory_mgr.get_chat_history(user_id)), 0)

        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()
