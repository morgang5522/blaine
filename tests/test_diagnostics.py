import unittest
import asyncio
import tempfile
import os
from src.memory import SQLiteMemoryManager
from src.tools.diagnostics import DiagnosticsTool
import src.tools.diagnostics as diag_module

class TestDiagnosticsTool(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tmp_dir.name, "test_blaine_diag.db")
        self.memory = SQLiteMemoryManager(db_path=db_path)
        
        # Inject test memory manager
        diag_module.memory_manager = self.memory
        self.diag_tool = DiagnosticsTool()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_diagnostics_execution(self):
        async def run_test():
            res = await self.diag_tool.execute()
            self.assertEqual(res["status"], "SUCCESS")
            self.assertIn("hostname", res)
            self.assertIn("is_docker", res)
            self.assertIn("uptime_seconds", res)
            self.assertIn("load_avg", res)
            self.assertIn("disk", res)
            self.assertIn("database", res)
            self.assertIn("redis", res)

            msg = res.get("message", "")
            self.assertIn("Blaine System Diagnostics", msg)
            self.assertIn("SQLite DB", msg)
            self.assertIn("Disk Storage", msg)

        asyncio.run(run_test())

    def test_database_counts(self):
        async def run_test():
            # Add dummy data
            self.memory.add_chat_message(101, "user", "Hello Blaine")
            self.memory.store_fact(101, "favorite_color", "blue")
            self.memory.add_list_item(101, "groceries", "Milk")

            res = await self.diag_tool.execute()
            self.assertEqual(res["status"], "SUCCESS")
            counts = res["database"]["counts"]
            self.assertEqual(counts["messages"], 1)
            self.assertEqual(counts["facts"], 1)
            self.assertEqual(counts["lists"], 1)

        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()
