# core/planner.py
from models.llm import LocalLLM

PLANNER_SYSTEM_PROMPT = """
You are a planning assistant.

Your task:
- Understand the user's request
- Break it into clear, ordered steps
- Do NOT solve the task
- Do NOT write code

Return the plan as a numbered list.
"""

class Planner:
    def __init__(self, llm, memory, state):
        self.llm = llm
        self.memory = memory
        self.state = state

    def plan(self, user_input: str) -> str:
        prompt = f"""
TASK STATE:
{self.state.summary()}

CONVERSATION CONTEXT:
{self.memory.context()}

USER REQUEST:
{user_input}
"""

        return self.llm.generate(
            system_prompt=PLANNER_SYSTEM_PROMPT,
            user_prompt=prompt
        )
