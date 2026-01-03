# core/memory.py
from typing import List, Dict


class ShortTermMemory:
    def __init__(self, max_turns: int = 5):
        self.max_turns = max_turns
        self.history: List[Dict[str, str]] = []

    def add(self, role: str, content: str):
        self.history.append({"role": role, "content": content})
        if len(self.history) > self.max_turns * 2:
            self.history = self.history[-self.max_turns * 2 :]

    def context(self) -> str:
        """
        Returns formatted conversation context for the LLM.
        """
        return "\n".join(
            f"{item['role'].upper()}: {item['content']}"
            for item in self.history
        )
