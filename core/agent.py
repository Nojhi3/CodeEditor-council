# core/agent.py
import json
from models.prompts import BASE_SYSTEM_PROMPT


class Agent:
    def __init__(self, llm, memory, state):
        self.llm = llm
        self.memory = memory
        self.state = state

    def run(self, user_input: str, plan: str) -> str:
        prompt = f"""
TASK STATE:
{self.state.summary()}

PLAN:
{plan}

TASK:
{user_input}
"""

        return self.llm.generate(
            system_prompt=BASE_SYSTEM_PROMPT,
            user_prompt=prompt
        )
