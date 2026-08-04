import logging
from typing import Dict, Any
from src.tools.base import BaseTool
from src.memory import memory_manager

logger = logging.getLogger("blaine.tools.lists")

class ManageListTool(BaseTool):
    @property
    def name(self) -> str:
        return "manage_list"

    @property
    def description(self) -> str:
        return "Manages custom user lists (e.g. shopping list, to-do list, ideas list) by adding, removing, viewing, or clearing items."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "integer",
                    "description": "Telegram user ID."
                },
                "action": {
                    "type": "string",
                    "description": "Action: 'add', 'remove', 'view', or 'clear'.",
                    "default": "view"
                },
                "list_name": {
                    "type": "string",
                    "description": "Name of the list (e.g. 'shopping', 'todo', 'ideas').",
                    "default": "todo"
                },
                "item": {
                    "type": "string",
                    "description": "The item text to add or remove."
                }
            },
            "required": ["user_id", "list_name"]
        }

    async def execute(self, **kwargs) -> Dict[str, Any]:
        user_id = kwargs.get("user_id", 0)
        action = kwargs.get("action", "view").lower()
        list_name = kwargs.get("list_name", "todo").lower()
        item = kwargs.get("item", "")

        if action == "add" and item:
            memory_manager.add_list_item(user_id, list_name, item)
            return {"status": "SUCCESS", "message": f"Added '{item}' to your {list_name} list."}
        
        elif action == "remove" and item:
            removed = memory_manager.remove_list_item(user_id, list_name, item)
            msg = f"Removed '{item}' from {list_name} list." if removed else f"Item '{item}' not found in {list_name} list."
            return {"status": "SUCCESS", "message": msg}

        elif action == "clear":
            memory_manager.clear_list(user_id, list_name)
            return {"status": "SUCCESS", "message": f"Cleared your {list_name} list."}

        else: # view
            items = memory_manager.get_list_items(user_id, list_name)
            if not items:
                return {"status": "SUCCESS", "message": f"Your {list_name} list is currently empty."}
            return {
                "status": "SUCCESS",
                "list_name": list_name,
                "items": items,
                "message": f"Your {list_name} list:\n" + "\n".join([f"• {i}" for i in items])
            }
