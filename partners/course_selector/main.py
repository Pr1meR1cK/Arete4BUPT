"""Arete4BUPT Partner Agent — 选课助手 (FastAPI)"""

import toml
import json
import httpx

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
    
    # 1. 加载配置文件
    try:
        with open("config.toml", "r", encoding="utf-8") as f:
            config = toml.load(f)
        with open("prompts.toml", "r", encoding="utf-8") as f:
            prompts = toml.load(f)
        with open("acs.json", "r", encoding="utf-8") as f:
            acs = json.load(f)
    except Exception as e:
        return TaskResponse(
            task_id=req.task_id,
            status="error",
            result={"message": f"配置文件加载失败: {str(e)}"}
        )

    user_message = req.payload.get("message", "")
    
    # ==========================================
    # Phase 1: Decision (决策)
    # ==========================================
    decision_sys = prompts["decision"]["system"]
    decision_usr = prompts["decision"]["user"].format(request_body=user_message)
    
    llm_cfg = config["llm"]["default"]
    decision_resp = httpx.post(
        f"{llm_cfg['base_url'].rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {llm_cfg['api_key']}", "Content-Type": "application/json"},
        json={
            "model": llm_cfg["model"],
            "messages": [
                {"role": "system", "content": decision_sys},
                {"role": "user", "content": decision_usr}
            ],
            "temperature": 0.1
        },
        timeout=30.0
    )
    
    if decision_resp.status_code != 200:
        return TaskResponse(task_id=req.task_id, status="error", result={"message": "LLM调用失败(Decision)"})
    
    decision_content = decision_resp.json()["choices"][0]["message"]["content"]
    if "```json" in decision_content:
        decision_content = decision_content.split("```json")[1].split("```")[0].strip()
    elif "```" in decision_content:
        decision_content = decision_content.split("```")[1].split("```")[0].strip()
        
    decision_result = json.loads(decision_content)
    
    if not decision_result.get("accepted", False):
        return TaskResponse(
            task_id=req.task_id,
            status="rejected",
            result={"reason": decision_result.get("reason", "不在服务范围内")}
        )

    # ==========================================
    # Phase 2: Analysis (分析)
    # ==========================================
    analysis_sys = prompts["analysis"]["system"]
    analysis_usr = prompts["analysis"]["user"].format(
        original_request=user_message,
        context=json.dumps(req.payload, ensure_ascii=False)
    )
    
    analysis_resp = httpx.post(
        f"{llm_cfg['base_url'].rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {llm_cfg['api_key']}", "Content-Type": "application/json"},
        json={
            "model": llm_cfg["model"],
            "messages": [
                {"role": "system", "content": analysis_sys},
                {"role": "user", "content": analysis_usr}
            ],
            "temperature": 0.1
        },
        timeout=30.0
    )
    
    if analysis_resp.status_code != 200:
        return TaskResponse(task_id=req.task_id, status="error", result={"message": "LLM调用失败(Analysis)"})
        
    analysis_content = analysis_resp.json()["choices"][0]["message"]["content"]
    if "```json" in analysis_content:
        analysis_content = analysis_content.split("```json")[1].split("```")[0].strip()
    elif "```" in analysis_content:
        analysis_content = analysis_content.split("```")[1].split("```")[0].strip()
        
    analysis_result = json.loads(analysis_content)
    
    if analysis_result.get("missing"):
        return TaskResponse(
            task_id=req.task_id,
            status="need_info",
            result={
                "questions": analysis_result.get("questions", []),
                "missing": analysis_result.get("missing", [])
            }
        )

    # ==========================================
    # Phase 3: Production (生产)
    # ==========================================
    production_sys = prompts["production"]["system"]
    
    mock_course_data = [
        {"name": "深度学习", "credit": 3, "prereq": "Python, 线性代数", "capacity": "剩余10人"},
        {"name": "计算机视觉", "credit": 2, "prereq": "深度学习", "capacity": "已满"},
        {"name": "自然语言处理", "credit": 3, "prereq": "机器学习", "capacity": "剩余25人"}
    ]
    
    production_usr = prompts["production"]["user"].format(
        params=json.dumps(analysis_result.get("params", {}), ensure_ascii=False),
        course_data=json.dumps(mock_course_data, ensure_ascii=False)
    )
    
    production_resp = httpx.post(
        f"{llm_cfg['base_url'].rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {llm_cfg['api_key']}", "Content-Type": "application/json"},
        json={
            "model": llm_cfg["model"],
            "messages": [
                {"role": "system", "content": production_sys},
                {"role": "user", "content": production_usr}
            ],
            "temperature": 0.1
        },
        timeout=30.0
    )
    
    if production_resp.status_code != 200:
        return TaskResponse(task_id=req.task_id, status="error", result={"message": "LLM调用失败(Production)"})
        
    production_content = production_resp.json()["choices"][0]["message"]["content"]
    if "```json" in production_content:
        production_content = production_content.split("```json")[1].split("```")[0].strip()
    elif "```" in production_content:
        production_content = production_content.split("```")[1].split("```")[0].strip()
        
    production_result = json.loads(production_content)
    
    return TaskResponse(
        task_id=req.task_id,
        status="completed",
        result={
            "message": production_result.get("message", "处理完成"),
            "data": production_result
        }
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=59221, reload=True)
