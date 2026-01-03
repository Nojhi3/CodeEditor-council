# core/tool_executor.py
from tools.registry import TOOLS


class ToolExecutor:
    def execute(self, tool_name: str, args: dict):
        if tool_name not in TOOLS:
            raise ValueError(f"Unknown tool: {tool_name}")

        tool = TOOLS[tool_name]
        return tool.run(**args)
