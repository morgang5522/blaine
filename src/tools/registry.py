import logging
from typing import Dict, List, Any
from src.tools.base import BaseTool
from src.tools.media import ArchiveMediaTool, CloudSyncTool
from src.tools.memory import (
    RememberUserFactTool,
    ForgetMemoryTool,
    UpdateMemoryTool,
    ListMemoriesTool,
    ClearAllMemoriesTool,
    ClearChatHistoryTool
)
from src.tools.reminders import (
    ScheduleReminderTool,
    CancelReminderTool,
    ListRemindersTool,
    AmendReminderTool
)
from src.tools.web_search import WebSearchTool
from src.tools.lists import ManageListTool
from src.tools.weather import WeatherTool
from src.tools.diagnostics import DiagnosticsTool

logger = logging.getLogger("blaine.tools.registry")

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def _register_default_tools(self):
        # Category 1 & Core Tools
        self.register(ArchiveMediaTool())
        self.register(CloudSyncTool())
        self.register(RememberUserFactTool())
        self.register(ForgetMemoryTool())
        self.register(UpdateMemoryTool())
        self.register(ListMemoriesTool())
        self.register(ClearAllMemoriesTool())
        self.register(ClearChatHistoryTool())

        # Category 3 Productivity Tools
        self.register(ScheduleReminderTool())
        self.register(CancelReminderTool())
        self.register(ListRemindersTool())
        self.register(AmendReminderTool())
        self.register(WebSearchTool())
        self.register(ManageListTool())
        
        self.register(WeatherTool())
        self.register(DiagnosticsTool())

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Returns JSON schema definitions for Gemini/LLM Function Calling."""
        schemas = []
        for tool in self._tools.values():
            schema_params = tool.parameters_schema.copy()
            if "properties" in schema_params:
                props = {k: v for k, v in schema_params["properties"].items() if k != "user_id"}
                reqs = [r for r in schema_params.get("required", []) if r != "user_id"]
                schema_params = {
                    "type": schema_params.get("type", "object"),
                    "properties": props
                }
                if reqs:
                    schema_params["required"] = reqs
            schemas.append({
                "name": tool.name,
                "description": tool.description,
                "parameters": schema_params
            })
        return schemas

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name not in self._tools:
            logger.error(f"Attempted execution of unregistered tool: '{tool_name}'")
            return {"status": "ERROR", "message": f"Tool '{tool_name}' is not registered."}

        tool = self._tools[tool_name]
        try:
            return await tool.execute(**arguments)
        except Exception as e:
            logger.exception(f"Error executing tool '{tool_name}': {e}")
            return {"status": "ERROR", "message": str(e)}

tool_registry = ToolRegistry()
