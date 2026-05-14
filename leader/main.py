"""Arete4BUPT Leader Agent — 个人课程助手 (FastAPI)"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

app = FastAPI(title="Arete4BUPT Leader", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class UserRequest(BaseModel):
    session_id: Optional[str] = None
    message: str


class TaskResult(BaseModel):
    session_id: str
    status: str  # pending | running | awaiting_input | completed | failed
    message: str
    data: Optional[dict] = None


@app.get("/health")
def health():
    return {"status": "ok", "agent": "Arete4BUPT Leader"}


@app.post("/api/v1/submit")
def submit(req: UserRequest):
    """接收学生提问，交给编排器处理"""
    # TODO: 意图分析 → 任务拆解 → Partner 调度 → 结果整合
    return {
        "session_id": req.session_id or "new-session-id",
        "status": "pending",
        "message": f"已收到: {req.message}",
    }


@app.get("/api/v1/result/{session_id}")
def get_result(session_id: str):
    """轮询任务状态和结果"""
    return {
        "session_id": session_id,
        "status": "pending",
        "message": "处理中...",
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=59210, reload=True)
