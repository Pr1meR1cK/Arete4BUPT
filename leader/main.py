"""Arete4BUPT Leader Agent — 个人课程助手 (FastAPI)"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

from assistant.orchestrator import orchestrate
from assistant.session import get_session_manager, TaskStatus

app = FastAPI(title="Arete4BUPT Leader", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class UserRequest(BaseModel):
    session_id: Optional[str] = None
    message: str


@app.get("/health")
def health():
    return {"status": "ok", "agent": "Arete4BUPT Leader"}


@app.post("/api/v1/submit")
async def submit(req: UserRequest):
    """接收学生提问，交给编排器处理 — 4 阶段流水线."""
    result = await orchestrate(req.session_id, req.message)
    return result


@app.get("/api/v1/result/{session_id}")
def get_result(session_id: str):
    """轮询任务状态和结果."""
    sm = get_session_manager()
    session = sm._sessions.get(session_id)
    if not session or not session.active_task_id:
        raise HTTPException(status_code=404, detail="会话不存在")

    task = session.tasks.get(session.active_task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return {
        "session_id": session.id,
        "active_task_id": session.active_task_id,
        "status": task.status,
        "message": (
            task.final_answer
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
            else task.clarification or "正在处理..."
        ),
        "task_detail": task.to_dict(),
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=59210, reload=True)
