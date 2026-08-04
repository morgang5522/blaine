import unittest
import asyncio
from unittest.mock import patch, MagicMock
from src.tools.web_search import WebSearchTool
from src.config import settings

class TestWebSearchTool(unittest.TestCase):
    def setUp(self):
        self.tool = WebSearchTool()

    def test_empty_query(self):
        async def run_test():
            res = await self.tool.execute(query="")
            self.assertEqual(res["status"], "ERROR")
            self.assertIn("No query provided", res["message"])

        asyncio.run(run_test())

    @patch.object(settings, "BRAVE_API_KEY", "test_brave_key")
    @patch.object(WebSearchTool, "_search_brave")
    def test_brave_search_success(self, mock_brave):
        mock_brave.return_value = [
            {
                "title": "Glendale, Arizona Official Website",
                "snippet": "City of Glendale government and visitor services.",
                "url": "https://www.glendaleaz.com/"
            }
        ]

        async def run_test():
            res = await self.tool.execute(query="Glendale Arizona information")
            self.assertEqual(res["status"], "SUCCESS")
            self.assertEqual(res["source"], "brave")
            self.assertEqual(len(res["results"]), 1)
            self.assertIn("Glendale, Arizona Official Website", res["summary"])
            self.assertIn("https://www.glendaleaz.com/", res["summary"])

        asyncio.run(run_test())

    @patch.object(settings, "BRAVE_API_KEY", "")
    def test_keyless_search_fallback(self):
        async def run_test():
            res = await self.tool.execute(query="Glendale Arizona")
            self.assertEqual(res["status"], "SUCCESS")
            self.assertIn(res["source"], ["keyless", "keyless_fallback"])
            self.assertTrue(len(res["results"]) > 0)
            self.assertIn("Glendale", res["summary"])

        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()
