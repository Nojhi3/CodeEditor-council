# core/orchestrator.py
import json
import re

from core.planner import Planner
from core.tool_executor import ToolExecutor
from core.memory import ShortTermMemory, LongTermMemory
from core.state import TaskState

from models.llm_factory import get_llm
from models.prompts import COMMON_INSTRUCTIONS, PLANNER_SYSTEM_PROMPT, EXECUTOR_SYSTEM_PROMPT, REFLECT_SYSTEM_PROMPT

class Orchestrator:
    def __init__(self, provider: str = "local"):
        self.llm = get_llm(provider)
        self.memory = ShortTermMemory()
        self.long_term_memory = LongTermMemory()
        self.state = TaskState()
        self.tool_executor = ToolExecutor()

        self.planner = Planner(self.llm, self.memory, self.state)

    # -------------------------
    # Public entry point
    # -------------------------
    def run(self, user_input: str):
        # -------------------------
        # Initialize task
        # -------------------------
        self.memory.add("user", user_input)
        self.state.set_task(user_input)

        # -------------------------
        # PLAN
        # -------------------------
        plan = self._plan_phase(user_input)
        self._validate_plan_output(plan)

        print("\n[PLAN]\n", plan)

        steps = [
            line.split(".", 1)[1].strip()
            for line in plan.splitlines()
            if line.strip() and line[0].isdigit()
        ]
        self.state.set_plan(steps)

        # -------------------------
        # EXECUTION LOOP
        # -------------------------
        while self.state.plan_valid and not self.state.is_complete():
            self._log_progress()

            if self.state.current_step() is None:
                break

            tool_call = self._execute_phase(user_input)

            # No action taken (analysis step or NO_ACTION)
            if tool_call is None:
                continue

            # -------------------------
            # TOOL EXECUTION (one per loop)
            # -------------------------
            tool_name = tool_call["tool"]
            tool_args = tool_call["args"]

            tool_result = self.tool_executor.execute(tool_name, tool_args)

            # Artifact tracking (write_file example)
            if tool_name == "write_file":
                self.state.add_artifact(
                    tool_args["path"],
                    role=self.state.expected_artifact_role or "unknown"
                )

            # After tool execution, advance step
            self.state.advance_step()
            self.state.clear_last_tool()

        # -------------------------
        # REFLECT (post-mortem)
        # -------------------------
        attempts = 0
        reflection = None

        while attempts < 2:
            attempts += 1

            reflection = self.llm.generate(
                system_prompt=REFLECT_SYSTEM_PROMPT,
                user_prompt=f"""
        TASK:
        {self.state.task}

        ARTIFACTS:
        {self.state.artifacts}

        Summarize what was done.
        Attempt {attempts}/2.
        """
            ).strip()

            if self._validate_reflection(reflection):
                break
        else:
            raise RuntimeError("Invalid reflection after retry")

        # -------------------------
        # Commit long-term memory (AFTER success)
        # -------------------------
        if reflection:
            self.long_term_memory.store(
                task=self.state.task,
                artifacts=self.state.artifacts,
                summary=reflection,
            )




        # -------------------------
        # DONE / FAIL
        # -------------------------
        if not self.state.plan_valid:
            raise RuntimeError(
                f"Task failed: {self.state.last_error}"
            )

        print("[DONE] Task completed successfully")

        return {
            "task": self.state.task,
            "steps_completed": self.state.current_step_index,
            "total_steps": len(self.state.plan),
            "artifacts": self.state.artifacts,
            "reflection": reflection,
        }


    # -------------------------
    # Phase implementations
    # -------------------------
    def _plan_phase(self, user_input: str) -> str:
        past = self.long_term_memory.recall(user_input)

        memory_hint = ""
        if past:
            memory_hint = (
                "\nPAST SUCCESSFUL OUTCOMES:\n"
                + "\n".join(
                    f"- {p['summary']} (artifacts: {p['artifacts']})"
                    for p in past
                )
            )

        return self.llm.generate(
            system_prompt=PLANNER_SYSTEM_PROMPT,
            user_prompt=f"""
    TASK STATE:
    {self.state.summary()}

    {memory_hint}

    CONVERSATION CONTEXT:
    {self.memory.context()}

    USER REQUEST:
    {user_input}

    Output ONLY the numbered plan.
    """
        )


    def _execute_phase(self, user_input: str):
        current_step = self.state.current_step()

        if current_step is None:
            return None

        # 1️⃣ Deterministic skip for non-executable steps
        step_type = self._normalize_step_type(current_step)

        if step_type == "NON_EXECUTABLE":
            self._log_progress()
            self.state.advance_step()
            return None

        # 2️⃣ STEP 5: Automatic artifact intent inference (BEFORE enforcement)
        if not self.state.has_artifact_intent():
            inferred = self._infer_artifact_intent(user_input, current_step)
            if inferred:
                name, role = inferred
                self.state.set_expected_artifact(name, role)

        # # 3️⃣ 🚫 EXECUTE requires artifact intent (ONLY for executable steps)
        # if not self.state.has_artifact_intent():
        #     self.state.invalidate_plan(
        #         "EXECUTE attempted without artifact intent"
        #     )
        #     self._log_progress()
        #     raise RuntimeError("EXECUTE blocked: no artifact intent")

        # 4️⃣ Attempt EXECUTE (max 2 tries)
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
                self._log_progress()
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
                    self._log_progress()
                    raise ValueError("Malformed tool call")

                return tool_call

            except Exception as e:
                last_error = str(e)

        # 5️⃣ Hard failure after retry
        self.state.invalidate_plan(
            f"EXECUTE failed after retry: {last_error}"
        )
        self._log_progress()
        raise RuntimeError("EXECUTE phase violation")

    
    def _validate_plan_output(self, plan: str):
        forbidden_code_tokens = [
            "def ", 
            "import ", 
            "```", 
            "print(", 
            "if __name__",
            "from ",
            "while "
        ]

        for token in forbidden_code_tokens:
            if token in plan:
                raise RuntimeError(
                    f"Planner violation: forbidden token detected -> {token}"
                )

        for line in plan.splitlines():
            line = line.strip()
            if not line:
                continue
            
            if line.lower().startswith(("plan", "here is")):
                continue

            if line.startswith(("*", "-")):
                raise RuntimeError(
                    "Planner violation: Bullet points/substeps detected"
                )
            
            

    def _infer_artifact_intent(self, user_input: str, current_step: str):
        """
        Determine expected artifact based on task + current step.
        This function must be deterministic and conservative.
        """

        task = user_input.lower()
        step = current_step.lower()

        # --------------------------------------------------
        # SAVE / WRITE / EXPORT steps (highest priority)
        # --------------------------------------------------
        if any(word in step for word in ["save", "write", "export", "persist"]):
            # CSV export
            if "csv" in step:
                return ("output.csv", "data")

            # JSON export
            if "json" in step:
                return ("output.json", "data")

            # Generic save fallback
            return ("output.txt", "data")

        # --------------------------------------------------
        # CODE GENERATION
        # --------------------------------------------------
        if any(word in task for word in ["python", "function", "script", "program"]):
            # ADD "define" and "code" to this list below
            if any(word in step for word in ["implement", "generate", "create", "define", "code"]): 
                return ("main.py", "code")

        # --------------------------------------------------
        # DOCUMENTATION
        # --------------------------------------------------
        if any(word in task for word in ["readme", "documentation", "doc"]):
            return ("README.md", "doc")

        return None
    

    def _log_progress(self):
        print(
            f"[PROGRESS] "
            f"Step {self.state.current_step_index + 1}"
            f"/{len(self.state.plan)} | "
            f"Current: {self.state.current_step()} | "
            f"Artifacts: {self.state.artifacts}"
        )

    def _validate_reflection(self, reflection: str) -> bool:
        if not self.state.artifacts:
            return False

        reflection_l = reflection.lower()

        # 1️⃣ Must mention at least one artifact
        if not any(artifact.lower() in reflection_l for artifact in self.state.artifacts):
            return False

        # 2️⃣ Must indicate completion or persistence
        completion_signals = (
            "saved",
            "written",
            "created",
            "stored",
            "persisted",
            "completed",
        )

        if not any(signal in reflection_l for signal in completion_signals):
            return False

        return True


    def _normalize_step_type(self, step: str) -> str:
        """
        Returns: 'NON_EXECUTABLE' or 'EXECUTABLE'
        """

        step_lower = step.lower()

        non_exec_verbs = (
            "analyze",
            "design",
            "define",
            "identify",
            "determine",
            "verify",
            "validate",
            "compare",
            "evaluate",
            "plan",
            "understand",
        )

        exec_verbs = (
            "save",
            "write",
            "export",
            "persist",
            "store",
        )

        for verb in non_exec_verbs:
            if step_lower.startswith(verb):
                return "NON_EXECUTABLE"

        for verb in exec_verbs:
            if step_lower.startswith(verb):
                return "EXECUTABLE"

        # Default: conservative
        return "NON_EXECUTABLE"
    
    









