# core/state.py
from typing import Dict, List, Optional


class TaskState:
    def __init__(self):
        # -------------------------
        # Task
        # -------------------------
        self.task: Optional[str] = None

        # -------------------------
        # Planning
        # -------------------------
        self.plan: List[str] = []
        self.current_step_index: int = 0
        self.plan_valid: bool = True

        # -------------------------
        # Artifact intent (KEY CHANGE)
        # -------------------------
        self.expected_artifact: Optional[str] = None
        self.expected_artifact_role: Optional[str] = None

        # -------------------------
        # Artifacts (actual outputs)
        # -------------------------
        self.artifacts: List[str] = []
        self.artifact_roles: Dict[str, str] = {}

        # -------------------------
        # Diagnostics
        # -------------------------
        self.last_error: Optional[str] = None
        # Tool chaining (controlled)
        self.last_tool: Optional[str] = None


    # =========================================================
    # Task / Plan management
    # =========================================================
    def set_task(self, task: str):
        self.task = task

        # Reset execution state
        self.plan = []
        self.current_step_index = 0
        self.plan_valid = True

        # Reset artifacts
        self.artifacts.clear()
        self.artifact_roles.clear()
        self.expected_artifact = None
        self.expected_artifact_role = None
        self.last_tool = None


        # Reset diagnostics
        self.last_error = None

    def set_plan(self, plan_steps: List[str]):
        self.plan = plan_steps
        self.current_step_index = 0
        self.plan_valid = True

    def current_step(self) -> Optional[str]:
        if not self.plan_valid:
            return None
        if self.current_step_index >= len(self.plan):
            return None
        return self.plan[self.current_step_index]

    def advance_step(self):
        self.current_step_index += 1

    def invalidate_plan(self, reason: str):
        self.plan_valid = False
        self.last_error = reason

    def is_complete(self) -> bool:
        return self.plan_valid and self.current_step_index >= len(self.plan)

    # =========================================================
    # Artifact intent (EXECUTE gating)
    # =========================================================
    def set_expected_artifact(self, name: str, role: str):
        self.expected_artifact = name
        self.expected_artifact_role = role

    def clear_expected_artifact(self):
        self.expected_artifact = None
        self.expected_artifact_role = None

    def has_artifact_intent(self) -> bool:
        return self.expected_artifact is not None

    # =========================================================
    # Artifact tracking (actual results)
    # =========================================================
    def add_artifact(self, name: str, role: str):
        if name not in self.artifacts:
            self.artifacts.append(name)

        self.artifact_roles[name] = role

        # Fulfill intent if this was expected
        if self.expected_artifact == name:
            self.clear_expected_artifact()

    # =========================================================
    # Introspection (debug + prompt context)
    # =========================================================
    def summary(self) -> str:
        plan_info = (
            "\n".join(
                f"{i+1}. {step}"
                for i, step in enumerate(self.plan)
            )
            if self.plan else "None"
        )

        artifact_info = "\n".join(
            f"- {name}: {self.artifact_roles.get(name, 'unknown')}"
            for name in self.artifacts
        )

        return f"""
TASK:
{self.task or "None"}

PLAN VALID:
{self.plan_valid}

CURRENT STEP:
{self.current_step() or "None"}

EXPECTED ARTIFACT:
{self.expected_artifact or "None"} ({self.expected_artifact_role or "None"})

PLAN:
{plan_info}

ARTIFACTS:
{artifact_info if artifact_info else "None"}

LAST ERROR:
{self.last_error or "None"}
"""
    def record_tool(self, tool_name: str):
        self.last_tool = tool_name

    def clear_last_tool(self):
        self.last_tool = None

