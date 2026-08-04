import unittest
import asyncio
import tempfile
import os
from src.memory import SQLiteMemoryManager
from src.tools.weather import WeatherTool
import src.tools.weather as weather_module

class TestWeatherTool(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tmp_dir.name, "test_blaine_weather.db")
        self.memory = SQLiteMemoryManager(db_path=db_path)
        
        # Inject test memory manager into weather module
        weather_module.memory_manager = self.memory
        self.weather_tool = WeatherTool()
        self.user_id = 999111

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_weather_location_name(self):
        async def run_test():
            res = await self.weather_tool.execute(location="London")
            self.assertEqual(res["status"], "SUCCESS")
            self.assertIn("London", res["location_name"])
            self.assertIsNotNone(res["current_temp_c"])
            self.assertIsNotNone(res["condition"])
            self.assertIn("Weather for", res["message"])

        asyncio.run(run_test())

    def test_weather_birmingham_uk(self):
        async def run_test():
            res = await self.weather_tool.execute(location="Birmingham, UK")
            self.assertEqual(res["status"], "SUCCESS")
            self.assertIn("Birmingham", res["location_name"])
            self.assertIn("United Kingdom", res["location_name"])
            self.assertIsNotNone(res["current_temp_c"])

        asyncio.run(run_test())

    def test_weather_coordinates(self):
        async def run_test():
            res = await self.weather_tool.execute(latitude=35.6762, longitude=139.6503, location="Tokyo, Japan")
            self.assertEqual(res["status"], "SUCCESS")
            self.assertIn("Tokyo", res["location_name"])
            self.assertIsNotNone(res["current_temp_c"])
            self.assertIsNotNone(res["current_temp_f"])

        asyncio.run(run_test())

    def test_weather_memory_fallback(self):
        async def run_test():
            # Save home location for test user
            self.memory.store_fact(self.user_id, "home_location", "Paris")

            # Execute without location string or coordinates
            res = await self.weather_tool.execute(user_id=self.user_id)
            self.assertEqual(res["status"], "SUCCESS")
            self.assertIn("Paris", res["location_name"])

        asyncio.run(run_test())

    def test_weather_no_location_error(self):
        async def run_test():
            # Execute with user that has no location fact
            res = await self.weather_tool.execute(user_id=777888)
            self.assertEqual(res["status"], "ERROR")
            self.assertIn("No location specified", res["message"])

        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()
