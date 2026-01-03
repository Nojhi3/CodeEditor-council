# core/orchestrator.py
import json
import re

from core.planner import Planner
from core.tool_executor import ToolExecutor
from core.memory import ShortTermMemory
from core.state import TaskState

from models.llm_factory import get_llm
from models.prompts import COMMON_INSTRUCTIONS, PLANNER_SYSTEM_PROMPT, EXECUTOR_SYSTEM_PROMPT

class Orchestrator:
    def __init__(self, provider: str = "local"):
        self.llm = get_llm(provider)
        self.memory = ShortTermMemory()
        self.state = TaskState()
        self.tool_executor = ToolExecutor()

        self.planner = Planner(self.llm, self.memory, self.state)

    # -------------------------
    # Public entry point
    # -------------------------
    def run(self, user_input: str) -> str:
        self.memory.add("user", user_input)
        self.state.set_task(user_input)

        # 1️⃣ PLAN_ONLY
        plan = self._plan_phase(user_input)
        print("\n[PLAN]\n", plan)
        
        self._validate_plan_output(plan)
        
        # IMPROVED PARSING: Use regex to capture "1. Step..." or "1 Step..."
        steps = []
        for line in plan.splitlines():
            # Matches "1. Step text" or "1 Step text"
            match = re.match(r"^\d+[\.\)]\s*(.*)", line.strip())
            if match:
                steps.append(match.group(1))
        
        self.state.set_plan(steps)

        # 2️⃣ EXECUTE
        tool_call = self._execute_phase(user_input)

        # If no tool needed, stop here
        if tool_call is None:
            self.memory.add("assistant", plan)
            return plan

        # 3️⃣ TOOL EXECUTION
        tool_name = tool_call["tool"]
        tool_args = tool_call["args"]

        tool_result = self.tool_executor.execute(tool_name, tool_args)

        if tool_name == "write_file":
            self.state.add_artifact(
                tool_args["path"],
                role="generated_code"
            )

        # 4️⃣ REFLECT
        final_response = self._reflect_phase(tool_result)

        self.memory.add("user", user_input)
        return final_response

    # -------------------------
    # Phase implementations
    # -------------------------
    def _plan_phase(self, user_input: str) -> str:
        return self.llm.generate(
            system_prompt=PLANNER_SYSTEM_PROMPT,  # Use dedicated prompt
            user_prompt=f"""
                CONTEXT:
                {self.memory.context()}

                USER REQUEST:
                {user_input}
                
                Generate the high-level plan now.
                """
        )

    def _execute_phase(self, user_input: str):
        current_step = self.state.current_step()

        if current_step is None:
            return None

        # 1️⃣ Deterministic skip for non-executable steps
        NON_EXECUTABLE_PREFIXES = (
            "Analyze",
            "Design",
            "Identify",
            "Prepare",
            "Determine",
        )

        if current_step.startswith(NON_EXECUTABLE_PREFIXES):
            self.state.advance_step()
            return None

        # 2️⃣ 🚫 EXECUTE requires artifact intent (ONLY for executable steps)
        if not self.state.has_artifact_intent():
            self.state.invalidate_plan(
                "EXECUTE attempted without artifact intent"
            )
            raise RuntimeError("EXECUTE blocked: no artifact intent")

        # 3️⃣ Attempt EXECUTE (max 2 tries)
        attempts = 0
        last_error = None

        while attempts < 2:
            attempts += 1

            response = self.llm.generate(
                system_prompt=EXECUTOR_SYSTEM_PROMPT,
                user_prompt=f"""
    TASK:
    {self.state.task}

    CURRENT STEP:
    {current_step}

    STRICT RULES:
    - Return ONLY valid JSON OR the string NO_ACTION
    - Do NOT explain
    - Do NOT summarize
    - Do NOT plan
    - Do NOT include extra text

    This is attempt {attempts}/2.
    """
            ).strip()

            # ✅ Explicit NO_ACTION
            if response == "NO_ACTION":
                self.state.advance_step()
                return None

            # ✅ Try parsing JSON
            try:
                tool_call = json.loads(response)

                if (
                    not isinstance(tool_call, dict)
                    or "tool" not in tool_call
                    or "args" not in tool_call
                ):
                    raise ValueError("Malformed tool call")

                return tool_call

            except Exception as e:
                last_error = str(e)

        # 4️⃣ Hard failure after retry
        self.state.invalidate_plan(
            f"EXECUTE failed after retry: {last_error}"
        )
        raise RuntimeError("EXECUTE phase violation")



    def _reflect_phase(self, tool_result: str) -> str:
        return self.llm.generate(
            system_prompt=COMMON_INSTRUCTIONS,
            user_prompt=f"""
                TASK STATE:
                {self.state.summary()}

                TOOL RESULT:
                {tool_result}

                Provide the final response.
                """
        )
    
    def _validate_plan_output(self, plan: str):
        forbidden_code_tokens = [
            "def ", "class ", "import ", "return ", 
            "```", "print(", "if __name__"
        ]

        for token in forbidden_code_tokens:
            if token in plan:
                raise RuntimeError(
                    f"Planner violation: forbidden token detected -> {token}"
                )

        for line in plan.splitlines():
            if ":" in line or "*" in line or "-" in line:
                raise RuntimeError(
                    "Planner violation: explanations or substeps detected"
                )


