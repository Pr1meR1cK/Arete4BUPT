"""Arete4BUPT Partner Agent — 选课助手 (FastAPI)"""

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Arete4BUPT 选课助手", version="0.1.0")


class TaskRequest(BaseModel):
    task_id: str
    command: str
    payload: dict


class TaskResponse(BaseModel):
    task_id: str
    status: str
    result: dict


@app.get("/health")
def health():
    return {"status": "ok", "agent": "选课助手"}


@app.post("/rpc")
def handle_task(req: TaskRequest):
    """三阶段处理: Decision → Analysis → Production"""
    # TODO: 1. Decision — 判断请求是否在服务范围
    # TODO: 2. Analysis — 将需求转为结构化参数，识别缺失信息
    # TODO: 3. Production — 生成最终结果
    return {
        "task_id": req.task_id,
        "status": "completed",
        "result": {"message": "选课助手处理完成（模板）"},
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=59221, reload=True)
