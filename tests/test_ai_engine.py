import unittest
import asyncio
from unittest.mock import patch, MagicMock
from src.ai_engine import BlaineAIEngine

class TestAIEngineContext(unittest.TestCase):

    @patch("src.ai_engine.memory_manager")
    def test_multi_turn_contents_building(self, mock_mem):
        mock_mem.get_user_facts_summary.return_value = "No prior saved preferences."
        mock_mem.get_active_reminders.return_value = []
        mock_mem.get_user_timezone.return_value = None

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

    @patch("src.ai_engine.memory_manager")
    @patch("src.ai_engine.tool_registry")
    def test_list_reminders_synthesis(self, mock_registry, mock_mem):
        mock_mem.get_user_facts_summary.return_value = "No prior saved preferences."
        mock_mem.get_active_reminders.return_value = [{"id": 1, "reminder_text": "Check oven", "trigger_at": "2026-08-05 09:00:00"}]
        mock_mem.get_chat_history.return_value = [{"role": "user", "content": "What are my reminders?"}]
        mock_mem.get_user_timezone.return_value = None

        async def dummy_execute(name, args):
            return {"status": "SUCCESS", "message": "<b>Your active reminders:</b>\n• <b>[1]</b> Check oven", "reminders": [{"id": 1}]}

        mock_registry.execute_tool.side_effect = dummy_execute

        engine = BlaineAIEngine()
        mock_client = MagicMock()
        engine.client = mock_client

        # Turn 1 response returns list_reminders function call
        mock_call = MagicMock()
        mock_call.name = "list_reminders"
        mock_call.args = {}

        mock_resp1 = MagicMock()
        mock_resp1.function_calls = [mock_call]
        mock_resp1.text = ""
        mock_resp1.candidates = [MagicMock(content=MagicMock())]

        # Turn 2 response returns synthesized text
        mock_resp2 = MagicMock()
        mock_resp2.function_calls = None
        mock_resp2.text = "You have 1 active reminder: Check oven (due at 2026-08-05 09:00:00 UTC)."

        mock_client.models.generate_content.side_effect = [mock_resp1, mock_resp2]

        mock_genai_module = MagicMock()
        mock_types = MagicMock()
        mock_genai_module.types = mock_types

        class DummyContent:
            def __init__(self, role=None, parts=None):
                self.role = role
                self.parts = parts or []

        class DummyPart:
            @staticmethod
            def from_text(text):
                p = MagicMock()
                p.text = text
                return p
            @staticmethod
            def from_function_response(name, response):
                p = MagicMock()
                p.name = name
                p.response = response
                return p

        mock_types.Content = DummyContent
        mock_types.Part = DummyPart
        mock_types.Tool = MagicMock()
        mock_types.FunctionDeclaration = MagicMock()
        mock_types.GenerateContentConfig = MagicMock()

        async def run_test():
            with patch.dict("sys.modules", {"google": MagicMock(), "google.genai": mock_genai_module, "google.genai.types": mock_types}):
                result = await engine.parse_and_respond("What are my reminders?", user_id=123)

                # Verify 2nd turn synthesis happened and reply_text was captured
                self.assertEqual(result["reply_text"], "You have 1 active reminder: Check oven (due at 2026-08-05 09:00:00 UTC).")
                self.assertEqual(len(result["tool_calls"]), 1)
                self.assertEqual(result["tool_calls"][0]["name"], "list_reminders")

                # Verify synthesized response text was saved into memory chat messages
                mock_mem.add_chat_message.assert_any_call(123, "model", "You have 1 active reminder: Check oven (due at 2026-08-05 09:00:00 UTC).")

        asyncio.run(run_test())

    @patch("src.ai_engine.memory_manager")
    def test_ai_engine_user_timezone_prompt_building(self, mock_mem):
        import zoneinfo
        tz_obj = zoneinfo.ZoneInfo("America/New_York")
        mock_mem.get_user_timezone.return_value = (tz_obj, "America/New_York")
        mock_mem.get_user_facts_summary.return_value = "No prior saved preferences."
        mock_mem.get_active_reminders.return_value = []
        mock_mem.get_chat_history.return_value = [{"role": "user", "content": "Hello"}]

        engine = BlaineAIEngine()
        mock_client = MagicMock()
        engine.client = mock_client

        mock_response = MagicMock()
        mock_response.function_calls = None
        mock_response.text = "Hello there!"
        mock_client.models.generate_content.return_value = mock_response

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

        class DummyConfig:
            def __init__(self, system_instruction=None, **kwargs):
                self.system_instruction = system_instruction

        mock_types.Content = DummyContent
        mock_types.Part = DummyPart
        mock_types.GenerateContentConfig = DummyConfig

        async def run_test():
            with patch.dict("sys.modules", {"google": MagicMock(), "google.genai": mock_genai_module, "google.genai.types": mock_types}):
                await engine._process_with_gemini("Hello", 123, [{"role": "user", "content": "Hello"}], "")
                call_kwargs = mock_client.models.generate_content.call_args.kwargs
                sys_inst = call_kwargs["config"].system_instruction
                self.assertIn("Current UTC Time:", sys_inst)
                self.assertIn("User's Local Time:", sys_inst)
                self.assertIn("America/New_York", sys_inst)

        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()
