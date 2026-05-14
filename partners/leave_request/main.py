"""Arete4BUPT Partner Agent — 请假助手 (FastAPI)"""

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Arete4BUPT 请假助手", version="0.1.0")


class TaskRequest(BaseModel):
    task_id: str
    command: str
    payload: dict


@app.get("/health")
def health():
    return {"status": "ok", "agent": "请假助手"}


@app.post("/rpc")
def handle_task(req: TaskRequest):
    return {
        "task_id": req.task_id,
        "status": "completed",
        "result": {"message": "请假助手处理完成（模板）"},
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=59222, reload=True)
