# api/app.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from core.orchestrator import Orchestrator

app = FastAPI(title="LLM Execution Engine")

orchestrator = Orchestrator(provider="local")


class TaskRequest(BaseModel):
    task: str


class TaskResponse(BaseModel):
    task: str
    steps_completed: int
    total_steps: int
    artifacts: List[str]
    reflection: Optional[str] = None


@app.post("/run", response_model=TaskResponse)
def run_task(req: TaskRequest):
    try:
        result = orchestrator.run(req.task)
        return result
    except Exception as e:
        # Surface engine failures clearly
        raise HTTPException(status_code=400, detail=str(e))
