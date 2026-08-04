import unittest
import asyncio
from unittest.mock import patch, MagicMock
from src.ai_engine import BlaineAIEngine

class TestAIEngineContext(unittest.TestCase):

    @patch("src.ai_engine.memory_manager")
    def test_multi_turn_contents_building(self, mock_mem):
        mock_mem.get_user_facts_summary.return_value = "No prior saved preferences."
        mock_mem.get_active_reminders.return_value = []

        chat_history = [
            {"role": "user", "content": "My favorite team is the Jaguars"},
            {"role": "model", "content": "Nice! The Jacksonville Jaguars are a great team."},
            {"role": "user", "content": "Tell me who they got in the latest draft"}
        ]
        mock_mem.get_chat_history.return_value = chat_history

        engine = BlaineAIEngine()
        mock_client = MagicMock()
        engine.client = mock_client

        mock_response = MagicMock()
        mock_response.function_calls = None
        mock_response.text = "Here are the Jaguars' latest draft picks."
        mock_client.models.generate_content.return_value = mock_response

        # Mock google.genai types
        mock_genai_module = MagicMock()
        mock_types = MagicMock()
        mock_genai_module.types = mock_types

        class DummyContent:
            def __init__(self, role, parts):
                self.role = role
                self.parts = parts

        class DummyPart:
            @staticmethod
            def from_text(text):
                p = MagicMock()
                p.text = text
                return p

        mock_types.Content = DummyContent
        mock_types.Part = DummyPart

        async def run_test():
            with patch.dict("sys.modules", {"google": MagicMock(), "google.genai": mock_genai_module, "google.genai.types": mock_types}):
                result = await engine._process_with_gemini(
                    user_message="Tell me who they got in the latest draft",
                    user_id=123,
                    chat_history=chat_history,
                    memory_summary=""
                )
                self.assertEqual(result["reply_text"], "Here are the Jaguars' latest draft picks.")

                mock_client.models.generate_content.assert_called_once()
                call_kwargs = mock_client.models.generate_content.call_args.kwargs
                contents = call_kwargs["contents"]

                self.assertEqual(len(contents), 3)
                self.assertEqual(contents[0].role, "user")
                self.assertEqual(contents[0].parts[0].text, "My favorite team is the Jaguars")
                self.assertEqual(contents[1].role, "model")
                self.assertEqual(contents[1].parts[0].text, "Nice! The Jacksonville Jaguars are a great team.")
                self.assertEqual(contents[2].role, "user")
                self.assertEqual(contents[2].parts[0].text, "Tell me who they got in the latest draft")

        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()
