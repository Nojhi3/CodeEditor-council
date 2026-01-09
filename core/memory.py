# core/memory.py
from typing import List, Dict
import json
import os


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
    

class LongTermMemory:
    def __init__(self, path: str = "memory/long_term.json"):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                self.data: List[Dict] = json.load(f)
        else:
            self.data = []

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    # -------------------------
    # Write (only on success)
    # -------------------------
    def store(self, task: str, artifacts: List[str], summary: str):
        record = {
            "task_signature": task.lower().strip(),
            "artifacts": artifacts,
            "summary": summary,
        }
        self.data.append(record)
        self._save()

    # -------------------------
    # Read (for planning bias)
    # -------------------------
    def recall(self, task: str) -> List[Dict]:
        task_l = task.lower()
        return [
            r for r in self.data
            if r["task_signature"] in task_l
            or task_l in r["task_signature"]
        ]
