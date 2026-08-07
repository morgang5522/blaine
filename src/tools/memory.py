import logging
from typing import Dict, Any, Optional
from src.tools.base import BaseTool
from src.memory import memory_manager

logger = logging.getLogger("blaine.tools.memory")

class RememberUserFactTool(BaseTool):
    @property
    def name(self) -> str:
        return "remember_user_fact"

    @property
    def description(self) -> str:
        return "Stores a SINGLE durable user preference, habit, identity detail, operational mode (e.g. 'User enabled dev mode'), or long-term fact into Blaine's persistent memory. Only call for facts with high long-term value, NOT transient chatter or one-off tasks. Always call separately for each distinct fact."


    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "integer",
                    "description": "Telegram user ID."
                },
                "fact": {
                    "type": "string",
                    "description": "A single individual fact or mode setting (e.g. 'User's name is John', 'User is in dev mode', 'User works as a software engineer'). Do NOT combine multiple distinct facts into one string."
                }
            },
            "required": ["user_id", "fact"]
        }

    async def execute(self, **kwargs) -> Dict[str, Any]:
        user_id = kwargs.get("user_id", 0)
        fact = kwargs.get("fact", "")

        if not user_id or not fact:
            return {"status": "ERROR", "message": "Missing user_id or fact parameter."}

        saved = memory_manager.store_fact(user_id, "fact", fact)
        if saved:
            return {
                "status": "SUCCESS",
                "message": f"Saved to memory: '{fact}'",
                "is_new": True
            }
        else:
            return {
                "status": "SUCCESS",
                "message": f"Fact already known: '{fact}'",
                "is_new": False
            }


class ForgetMemoryTool(BaseTool):
    @property
    def name(self) -> str:
        return "forget_memory"

    @property
    def description(self) -> str:
        return "Deletes specific stored fact(s) or preference(s) from Blaine's long-term memory using a search keyword/topic or fact ID."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "integer",
                    "description": "Telegram user ID."
                },
                "fact_query": {
                    "type": "string",
                    "description": "Keyword or topic of the fact to forget (e.g. 'Jaguars', 'favorite team', 'coffee preference')."
                },
                "fact_id": {
                    "type": "integer",
                    "description": "Optional specific fact ID to delete."
                }
            },
            "required": ["user_id"]
        }

    async def execute(self, **kwargs) -> Dict[str, Any]:
        user_id = kwargs.get("user_id", 0)
        fact_query = kwargs.get("fact_query")
        fact_id = kwargs.get("fact_id")

        if not user_id:
            return {"status": "ERROR", "message": "Missing user_id parameter."}
        if not fact_query and fact_id is None:
            return {"status": "ERROR", "message": "Specify fact_query or fact_id to forget."}

        deleted = memory_manager.delete_fact(user_id, fact_id=fact_id, fact_query=fact_query)
        if deleted:
            names = ", ".join([f"'{d['fact_value']}'" for d in deleted])
            return {
                "status": "SUCCESS",
                "message": f"Forgotten from memory: {names}",
                "deleted_count": len(deleted),
                "deleted_facts": deleted
            }
        else:
            return {
                "status": "SUCCESS",
                "message": "No matching memory found to forget.",
                "deleted_count": 0
            }


class UpdateMemoryTool(BaseTool):
    @property
    def name(self) -> str:
        return "update_memory"

    @property
    def description(self) -> str:
        return "Updates an existing stored preference or fact in Blaine's long-term memory with new information."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "integer",
                    "description": "Telegram user ID."
                },
                "new_fact": {
                    "type": "string",
                    "description": "The updated fact value (e.g. 'User's favorite team is the Chiefs')."
                },
                "fact_query": {
                    "type": "string",
                    "description": "Keyword to find existing fact to replace (e.g. 'favorite team', 'coffee')."
                },
                "fact_id": {
                    "type": "integer",
                    "description": "Optional specific fact ID to update."
                }
            },
            "required": ["user_id", "new_fact"]
        }

    async def execute(self, **kwargs) -> Dict[str, Any]:
        user_id = kwargs.get("user_id", 0)
        new_fact = kwargs.get("new_fact", "")
        fact_query = kwargs.get("fact_query")
        fact_id = kwargs.get("fact_id")

        if not user_id or not new_fact:
            return {"status": "ERROR", "message": "Missing user_id or new_fact parameter."}

        updated = memory_manager.update_fact(user_id, new_fact, fact_id=fact_id, fact_query=fact_query)
        if updated:
            return {
                "status": "SUCCESS",
                "message": f"Memory updated to: '{updated['fact_value']}'",
                "updated_fact": updated
            }
        else:
            memory_manager.store_fact(user_id, "fact", new_fact)
            return {
                "status": "SUCCESS",
                "message": f"Saved new memory: '{new_fact}'",
                "is_new": True
            }


class ListMemoriesTool(BaseTool):
    @property
    def name(self) -> str:
        return "list_memories"

    @property
    def description(self) -> str:
        return "Lists all saved long-term memories, preferences, and facts currently stored for the user."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "integer",
                    "description": "Telegram user ID."
                }
            },
            "required": ["user_id"]
        }

    async def execute(self, **kwargs) -> Dict[str, Any]:
        user_id = kwargs.get("user_id", 0)
        if not user_id:
            return {"status": "ERROR", "message": "Missing user_id parameter."}

        facts = memory_manager.get_user_facts(user_id)
        if not facts:
            return {
                "status": "SUCCESS",
                "message": "No stored long-term memories found.",
                "facts": []
            }

        lines = [f"- [ID {f['id']}] {f['fact_value']}" for f in facts]
        summary_text = f"Stored Long-Term Memories ({len(facts)}):\n" + "\n".join(lines)
        return {
            "status": "SUCCESS",
            "message": summary_text,
            "facts": facts
        }


class ClearAllMemoriesTool(BaseTool):
    @property
    def name(self) -> str:
        return "clear_all_memories"

    @property
    def description(self) -> str:
        return "Clears ALL long-term memory facts and preferences stored for the user."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "integer",
                    "description": "Telegram user ID."
                }
            },
            "required": ["user_id"]
        }

    async def execute(self, **kwargs) -> Dict[str, Any]:
        user_id = kwargs.get("user_id", 0)
        if not user_id:
            return {"status": "ERROR", "message": "Missing user_id parameter."}

        count = memory_manager.clear_all_facts(user_id)
        return {
            "status": "SUCCESS",
            "message": f"Cleared all {count} long-term memories.",
            "cleared_count": count
        }


class ClearChatHistoryTool(BaseTool):
    @property
    def name(self) -> str:
        return "clear_chat_history"

    @property
    def description(self) -> str:
        return "Clears short-term conversational chat history for the user while preserving long-term saved facts and preferences."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "integer",
                    "description": "Telegram user ID."
                }
            },
            "required": ["user_id"]
        }

    async def execute(self, **kwargs) -> Dict[str, Any]:
        user_id = kwargs.get("user_id", 0)
        if not user_id:
            return {"status": "ERROR", "message": "Missing user_id parameter."}

        memory_manager.clear_chat_history(user_id)
        return {
            "status": "SUCCESS",
            "message": "Short-term chat history cleared. Long-term memory facts preserved."
        }
