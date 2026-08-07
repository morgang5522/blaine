import unittest
import asyncio
import tempfile
import os
from src.memory import SQLiteMemoryManager
from src.tools.reminders import (
    ScheduleReminderTool,
    CancelReminderTool,
    ListRemindersTool,
    AmendReminderTool
)

class TestReminderFeature(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tmp_dir.name, "test_blaine.db")
        self.memory = SQLiteMemoryManager(db_path=db_path)
        
        # Inject test memory manager into tools
        import src.tools.reminders as pt
        pt.memory_manager = self.memory

        self.schedule_tool = ScheduleReminderTool()
        self.cancel_tool = CancelReminderTool()
        self.list_tool = ListRemindersTool()
        self.amend_tool = AmendReminderTool()
        self.user_id = 12345
        self.chat_id = 67890

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_schedule_and_list_reminder(self):
        async def run_test():
            res1 = await self.schedule_tool.execute(
                user_id=self.user_id,
                chat_id=self.chat_id,
                reminder_text="Check the oven",
                duration_minutes=10
            )
            self.assertEqual(res1["status"], "SUCCESS")
            self.assertFalse(res1["is_duplicate"])
            rem_id = res1["reminder_id"]

            res_list = await self.list_tool.execute(user_id=self.user_id)
            self.assertEqual(res_list["status"], "SUCCESS")
            self.assertEqual(len(res_list["reminders"]), 1)
            self.assertEqual(res_list["reminders"][0]["id"], rem_id)
            self.assertEqual(res_list["reminders"][0]["reminder_text"], "Check the oven")
        
        asyncio.run(run_test())

    def test_duplicate_prevention(self):
        async def run_test():
            res1 = await self.schedule_tool.execute(
                user_id=self.user_id,
                chat_id=self.chat_id,
                reminder_text="Water the plants",
                duration_minutes=15
            )
            self.assertFalse(res1["is_duplicate"])

            # Attempting to schedule duplicate
            res2 = await self.schedule_tool.execute(
                user_id=self.user_id,
                chat_id=self.chat_id,
                reminder_text="water the plants",
                duration_minutes=15
            )
            self.assertTrue(res2["is_duplicate"])

            res_list = await self.list_tool.execute(user_id=self.user_id)
            self.assertEqual(len(res_list["reminders"]), 1)

        asyncio.run(run_test())

    def test_amend_reminder(self):
        async def run_test():
            res1 = await self.schedule_tool.execute(
                user_id=self.user_id,
                chat_id=self.chat_id,
                reminder_text="Check server logs",
                duration_minutes=30
            )
            rem_id = res1["reminder_id"]

            # Amend text and duration
            res_amend = await self.amend_tool.execute(
                user_id=self.user_id,
                reminder_id=rem_id,
                new_reminder_text="Check DigitalOcean server logs",
                new_duration_minutes=45
            )
            self.assertEqual(res_amend["status"], "SUCCESS")
            self.assertEqual(res_amend["reminder"]["reminder_text"], "Check DigitalOcean server logs")

            # Verify in active list
            res_list = await self.list_tool.execute(user_id=self.user_id)
            self.assertEqual(len(res_list["reminders"]), 1)
            self.assertEqual(res_list["reminders"][0]["reminder_text"], "Check DigitalOcean server logs")

        asyncio.run(run_test())

    def test_cancel_reminder_by_id_and_text(self):
        async def run_test():
            await self.schedule_tool.execute(
                user_id=self.user_id,
                chat_id=self.chat_id,
                reminder_text="Task A",
                duration_minutes=5
            )
            res2 = await self.schedule_tool.execute(
                user_id=self.user_id,
                chat_id=self.chat_id,
                reminder_text="Task B",
                duration_minutes=10
            )
            id_b = res2["reminder_id"]

            # Cancel Task B by ID
            res_cancel_b = await self.cancel_tool.execute(
                user_id=self.user_id,
                reminder_id=id_b
            )
            self.assertEqual(res_cancel_b["status"], "SUCCESS")

            # Verify only Task A remains
            res_list = await self.list_tool.execute(user_id=self.user_id)
            self.assertEqual(len(res_list["reminders"]), 1)
            self.assertEqual(res_list["reminders"][0]["reminder_text"], "Task A")

            # Cancel Task A by text search
            res_cancel_a = await self.cancel_tool.execute(
                user_id=self.user_id,
                reminder_text="Task A"
            )
            self.assertEqual(res_cancel_a["status"], "SUCCESS")

            # Verify list is empty
            res_list_empty = await self.list_tool.execute(user_id=self.user_id)
            self.assertEqual(len(res_list_empty["reminders"]), 0)

        asyncio.run(run_test())

    def test_target_time_iso_scheduling(self):
        async def run_test():
            target_iso = "2028-08-05 09:00:00"
            res = await self.schedule_tool.execute(
                user_id=self.user_id,
                chat_id=self.chat_id,
                reminder_text="Buy coffee tomorrow",
                target_time_iso=target_iso
            )
            self.assertEqual(res["status"], "SUCCESS")
            self.assertFalse(res["is_duplicate"])

            res_list = await self.list_tool.execute(user_id=self.user_id)
            self.assertEqual(len(res_list["reminders"]), 1)
            self.assertEqual(res_list["reminders"][0]["reminder_text"], "Buy coffee tomorrow")
            self.assertEqual(res_list["reminders"][0]["trigger_at"], "2028-08-05 09:00:00")

        asyncio.run(run_test())

    def test_user_timezone_parsing_and_reminder_display(self):
        async def run_test():
            # Store timezone preference fact
            self.memory.store_fact(self.user_id, "timezone", "America/New_York")
            tz_res = self.memory.get_user_timezone(self.user_id)
            self.assertIsNotNone(tz_res)
            self.assertEqual(tz_res[1], "America/New_York")

            # Schedule a reminder with absolute UTC time
            target_iso = "2028-08-05 14:00:00"
            res = await self.schedule_tool.execute(
                user_id=self.user_id,
                chat_id=self.chat_id,
                reminder_text="Team Sync",
                target_time_iso=target_iso
            )
            self.assertEqual(res["status"], "SUCCESS")
            # In America/New_York (EDT UTC-4), 14:00 UTC is 10:00
            self.assertIn("10:00 America/New_York", res["message"])

            # Verify list reminders shows local time display
            res_list = await self.list_tool.execute(user_id=self.user_id)
            self.assertEqual(len(res_list["reminders"]), 1)
            self.assertIn("10:00 America/New_York", res_list["message"])

        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()
