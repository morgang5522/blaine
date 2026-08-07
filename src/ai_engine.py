import datetime
import logging
from typing import Dict, Any, List
from src.config import settings
from src.tools.registry import tool_registry
from src.memory import memory_manager

logger = logging.getLogger("blaine.ai_engine")

BLAINE_SYSTEM_PROMPT = """You are Blaine, a warm, intelligent, authentic personal AI companion and assistant.

Behavior & Tone:
- Speak naturally and conversationally, like a close friend texting. Avoid robotic clichés ("As an AI...").
- Adaptive Persona: Dynamically adjust your tone, greeting, vocabulary, and conciseness to match the user's saved preferences in memory.
- Telegram Formatting: DO NOT use markdown headers or bold (*text*). Use plain text or standard Telegram HTML tags like <b>bold</b> or <code>code</code>. Emojis: maximum 1 subtle emoji.

Instructions:
- Maintain full context across turns. Resolve pronouns and implicit references using preceding conversation history.
- Contextual Queries: When executing search tools, construct explicit queries integrating subjects from prior turns.
- Time Context & Reminders: Use the Current System Date & Time and User's Local Time context. Reminders must ALWAYS be stored in UTC ('YYYY-MM-DD HH:MM:SS'). However, interpret user relative or local time expressions (e.g. '9am tomorrow', 'at 15:00', 'tonight at 8') using the User's Local Timezone if specified, converting them into target UTC timestamps before calling schedule_reminder or amend_reminder tools.
- Tool Usage: Only invoke tools for actions requested in the user's latest message turn. Synthesize tool execution results into natural, warm conversational text."""


class BlaineAIEngine:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL_NAME
        self.client = None
        self._init_client()

    def _init_client(self):
        try:
            from google import genai
            if self.api_key:
                self.client = genai.Client(api_key=self.api_key)
                logger.info(f"Initialized Gemini Client with model '{self.model_name}'")
            else:
                logger.warning("GEMINI_API_KEY missing. AI Engine running in rule-based fallback mode.")
        except ImportError:
            logger.warning("google-genai SDK not installed.")

    async def parse_and_respond(
        self,
        user_message: str,
        user_id: int = 0
    ) -> Dict[str, Any]:
        """
        Parses user input, retrieves chat history & memory facts, queries model, and saves turn to memory.
        """
        # Append incoming message to memory first
        memory_manager.add_chat_message(user_id, "user", user_message)

        chat_history = memory_manager.get_chat_history(user_id)
        memory_summary = memory_manager.get_user_facts_summary(user_id)

        if self.client:
            result = await self._process_with_gemini(user_message, user_id, chat_history, memory_summary)
        else:
            result = await self._fallback_rule_engine(user_message, memory_summary)

        reply_text = result.get("reply_text", "")
        tool_calls = result.get("tool_calls", [])

        if reply_text:
            memory_manager.add_chat_message(user_id, "model", reply_text)
        elif tool_calls:
            tool_names = ", ".join([c["name"] for c in tool_calls])
            memory_manager.add_chat_message(user_id, "model", f"[Processed tool request: {tool_names}]")

        return result

    async def _process_with_gemini(
        self,
        user_message: str,
        user_id: int,
        chat_history: List[Dict[str, str]],
        memory_summary: str
    ) -> Dict[str, Any]:
        try:
            from google.genai import types

            system_instruction = BLAINE_SYSTEM_PROMPT
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            time_str = now_utc.strftime("%A, %Y-%m-%d %H:%M:%S UTC")
            system_instruction += f"\n\nCurrent System Date & Time:\n- Current UTC Time: {time_str}"

            user_tz_res = memory_manager.get_user_timezone(user_id)
            if user_tz_res and isinstance(user_tz_res, tuple) and len(user_tz_res) == 2:
                user_tz_obj, user_tz_name = user_tz_res
                now_local = now_utc.astimezone(user_tz_obj)
                local_time_str = now_local.strftime("%A, %Y-%m-%d %H:%M:%S")
                system_instruction += f"\n- User's Local Time: {local_time_str} ({user_tz_name})"
            else:
                system_instruction += "\n- User's Local Timezone: Not set in memory (Defaulting to UTC)."

            if memory_summary and memory_summary != "No prior saved preferences.":
                system_instruction += f"\n\nUser Profile & Memory Context (CRITICAL: Dynamically adapt your speaking tone, persona, vocabulary, conciseness, and greeting to honor these saved facts and preferences):\n{memory_summary}"

            active_reminders = memory_manager.get_active_reminders(user_id)
            if active_reminders:
                rem_lines = []
                for r in active_reminders:
                    line = f"- [ID {r['id']}] '{r['reminder_text']}' due at {r['trigger_at']} UTC"
                    if user_tz_res and isinstance(user_tz_res, tuple) and len(user_tz_res) == 2:
                        try:
                            dt_naive = datetime.datetime.fromisoformat(r['trigger_at'])
                            dt_utc = dt_naive.replace(tzinfo=datetime.timezone.utc)
                            dt_local = dt_utc.astimezone(user_tz_res[0])
                            line += f" ({dt_local.strftime('%Y-%m-%d %H:%M')} {user_tz_res[1]})"
                        except Exception:
                            pass
                    rem_lines.append(line)
                system_instruction += "\n\nActive Pending Reminders for User:\n" + "\n".join(rem_lines)

            # Format tool declarations for Gemini Function Calling
            tools_list = [
                types.Tool(function_declarations=[
                    types.FunctionDeclaration(
                        name=s["name"], description=s["description"], parameters=s["parameters"]
                    )
                ]) for s in tool_registry.get_tool_schemas()
            ]

            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.6,
                max_output_tokens=2048,
                tools=tools_list
            )

            max_msgs = max(1, settings.MAX_CHAT_HISTORY_TURNS * 2)
            # Exclude current user_message (last element of chat_history) to format prior history as structured turns
            past_history = chat_history[:-1][-max_msgs:] if len(chat_history) > 1 else []

            contents: List[types.Content] = []

            if past_history:
                for msg in past_history:
                    role = "user" if msg["role"] == "user" else "model"
                    if contents and contents[-1].role == role:
                        contents[-1].parts.append(types.Part.from_text(text=msg["content"]))
                    else:
                        contents.append(
                            types.Content(
                                role=role,
                                parts=[types.Part.from_text(text=msg["content"])]
                            )
                        )

                if contents and contents[0].role == "model":
                    contents.pop(0)

            if contents and contents[-1].role == "user":
                contents[-1].parts.append(types.Part.from_text(text=user_message))
            else:
                contents.append(
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=user_message)]
                    )
                )

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config
            )

            tool_calls = []
            reply_text = ""

            if hasattr(response, 'function_calls') and response.function_calls:
                function_response_parts = []
                for call in response.function_calls:
                    args = dict(call.args) if hasattr(call, 'args') and call.args else {}
                    args["user_id"] = user_id
                    tool_calls.append({
                        "name": call.name,
                        "arguments": args
                    })

                    # Execute synchronous tools inline for Gemini 2nd turn collation & synthesis (excluding background Redis jobs)
                    if call.name != "archive_media":
                        try:
                            tool_result = await tool_registry.execute_tool(call.name, args)
                            function_response_parts.append(
                                types.Part.from_function_response(
                                    name=call.name,
                                    response={"result": tool_result}
                                )
                            )
                        except Exception as exec_err:
                            logger.error(f"Error executing tool '{call.name}' for AI synthesis: {exec_err}")
                            function_response_parts.append(
                                types.Part.from_function_response(
                                    name=call.name,
                                    response={"result": {"status": "ERROR", "message": str(exec_err)}}
                                )
                            )

                # If tools were executed for synthesis, request a 2nd turn from Gemini to collate and generate text
                if function_response_parts:
                    try:
                        contents.append(response.candidates[0].content)
                        contents.append(types.Content(role="user", parts=function_response_parts))

                        second_response = self.client.models.generate_content(
                            model=self.model_name,
                            contents=contents,
                            config=config
                        )

                        if hasattr(second_response, 'text') and second_response.text:
                            reply_text = second_response.text
                    except Exception as second_err:
                        logger.error(f"Error during Gemini 2nd turn synthesis: {second_err}")

            # Extract response text if not set by 2nd turn
            if not reply_text:
                try:
                    if hasattr(response, 'text') and response.text:
                        reply_text = response.text
                except Exception:
                    reply_text = ""

            # Default text fallback only if no tool call and no text
            if not reply_text and not tool_calls:
                reply_text = "I'm on it."

            # Fast link extraction check if no tool call was returned
            if not tool_calls and any(k in user_message for k in ["youtube.com/", "youtu.be/", "vimeo.com/", "tiktok.com/"]):
                words = user_message.split()
                target_url = next((w for w in words if w.startswith("http://") or w.startswith("https://")), None)
                if target_url:
                    tool_calls.append({
                        "name": "archive_media",
                        "arguments": {"url": target_url, "quality": "best", "category": "General", "cloud_target": "mega", "user_id": user_id}
                    })

            return {"reply_text": reply_text, "tool_calls": tool_calls}


        except Exception as e:
            logger.exception(f"Gemini API call error: {e}")
            return await self._fallback_rule_engine(user_message, memory_summary)

    async def _fallback_rule_engine(self, user_message: str, memory_summary: str) -> Dict[str, Any]:
        words = user_message.split()
        target_url = next((w for w in words if w.startswith("http://") or w.startswith("https://")), None)

        if target_url:
            reply = f"I've picked up the link you sent ({target_url}). I'll get that downloaded, organized, and synced to your cloud storage for you."
            tool_calls = [{
                "name": "archive_media",
                "arguments": {
                    "url": target_url,
                    "quality": "best",
                    "category": "General",
                    "cloud_target": "mega"
                }
            }]
        else:
            reply = "Hello. I'm Blaine, your assistant. Send me any message or media link whenever you'd like."
            tool_calls = []

        return {
            "reply_text": reply,
            "tool_calls": tool_calls
        }
