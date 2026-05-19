"""Arete4BUPT Partner Agent — 选课助手 (FastAPI) 符合交付标准版（已修复混合请求 & 返回格式）"""

import json
import toml
import httpx
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Arete4BUPT 选课助手", version="1.0.0")


class TaskRequest(BaseModel):
    task_id: str
    command: str
    payload: dict


class TaskResponse(BaseModel):
    task_id: str
    status: str
    result: dict


def parse_llm_json(content: str) -> dict:
    """统一解析LLM返回的JSON，兼容 ```json / ``` 包裹的情况"""
    content = content.strip()
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    return json.loads(content)


def call_llm(system_prompt: str, user_prompt: str, llm_cfg: dict, temperature: float = 0.1) -> dict:
    """封装LLM调用逻辑，统一处理异常"""
    try:
        resp = httpx.post(
            f"{llm_cfg['base_url'].rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {llm_cfg['api_key']}",
                "Content-Type": "application/json"
            },
            json={
                "model": llm_cfg["model"],
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": temperature
            },
            timeout=30.0
        )
        if resp.status_code != 200:
            return {"error": f"LLM调用失败，状态码：{resp.status_code}"}
        content = resp.json()["choices"][0]["message"]["content"]
        return parse_llm_json(content)
    except Exception as e:
        return {"error": f"LLM处理异常：{str(e)}"}


def extract_production_message(obj) -> str:
    """
    统一从 Production 结果中提取自然语言文本
    兼容：
    - 纯字符串
    - {"message": "..."}
    - {"reply": "..."}
    - 其他结构兜底
    """
    if isinstance(obj, str):
        return obj.strip()
    if isinstance(obj, dict):
        for key in ("message", "reply", "content", "text"):
            if key in obj and isinstance(obj[key], str):
                return obj[key].strip()
        return json.dumps(obj, ensure_ascii=False)
    return str(obj)


@app.get("/health")
def health():
    return {"status": "ok", "agent": "选课助手"}


@app.post("/rpc")
def handle_task(req: TaskRequest):
    """
    三阶段处理: Decision → Analysis → Production
    新增：
    - 混合请求 partial accept
    - Production 返回格式健壮性增强
    """
    try:
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
                status="failed",
                result={"message": f"配置文件加载失败: {str(e)}"}
            )

        # 提取请求核心内容
        user_message = req.payload.get("message", "")
        original_message = req.payload.get("original_message", {})
        depends_on_result = req.payload.get("depends_on_result", None)

        # ==========================================
        # Phase 1: Decision（准入判断）
        # ==========================================
        decision_sys = prompts["decision"]["system"]
        decision_usr = prompts["decision"]["user"].format(request_body=user_message)
        llm_cfg = config["llm"]["default"]

        decision_result = call_llm(decision_sys, decision_usr, llm_cfg)
        if "error" in decision_result:
            return TaskResponse(
                task_id=req.task_id,
                status="failed",
                result={"message": decision_result["error"]}
            )

        # 混合请求相关字段
        is_partial = decision_result.get("partial", False)
        reject_items = decision_result.get("reject_items", [])

        # 完全不在服务范围
        if not decision_result.get("accepted", False):
            # 如果不是 partial accept，直接失败
            if not is_partial:
                return TaskResponse(
                    task_id=req.task_id,
                    status="failed",
                    result={
                        "message": decision_result.get("reason", "不在服务范围内")
                    }
                )

        # ==========================================
        # Phase 2: Analysis（需求分析）
        # ==========================================
        analysis_sys = prompts["analysis"]["system"]
        analysis_usr = prompts["analysis"]["user"].format(
            original_request=user_message,
            context=json.dumps(
                {
                    "original_message": original_message,
                    "depends_on_result": depends_on_result
                },
                ensure_ascii=False
            )
        )

        analysis_result = call_llm(analysis_sys, analysis_usr, llm_cfg)
        if "error" in analysis_result:
            return TaskResponse(
                task_id=req.task_id,
                status="failed",
                result={"message": analysis_result["error"]}
            )

        # 信息不全，返回 awaiting_input
        if not analysis_result.get("is_complete", True):
            return TaskResponse(
                task_id=req.task_id,
                status="awaiting_input",
                result={
                    "message": analysis_result.get(
                        "clarification_question", "请补充选课相关信息"
                    )
                }
            )

        # ==========================================
        # Phase 3: Production（内容生成）
        # ==========================================
        production_sys = prompts["production"]["system"]

        # TODO: 替换为真实北邮课程接口数据
        mock_course_data = [
            {"name": "深度学习", "credit": 3, "prereq": "Python, 线性代数", "capacity": "剩余10人"},
            {"name": "计算机视觉", "credit": 2, "prereq": "深度学习", "capacity": "已满"},
            {"name": "自然语言处理", "credit": 3, "prereq": "机器学习", "capacity": "剩余25人"}
        ]

        production_usr = prompts["production"]["user"].format(
            params=json.dumps(
                analysis_result.get("extracted_params", {}), ensure_ascii=False
            ),
            course_data=json.dumps(mock_course_data, ensure_ascii=False)
        )

        production_result = call_llm(production_sys, production_usr, llm_cfg, temperature=0.3)
        if "error" in production_result:
            return TaskResponse(
                task_id=req.task_id,
                status="failed",
                result={"message": production_result["error"]}
            )

        # 统一提取自然语言文本
        final_message = extract_production_message(production_result)

        # 混合请求：追加拒绝说明（符合交付标准）
        if is_partial and reject_items:
            reject_text = "、".join(reject_items)
            final_message += (
                f"\n\n（温馨提示：{reject_text}相关请求不在选课助手服务范围内，"
                f"我已为你完成选课部分的解答。）"
            )

        return TaskResponse(
            task_id=req.task_id,
            status="completed",
            result={"message": final_message}
        )

    except Exception as e:
        return TaskResponse(
            task_id=req.task_id,
            status="failed",
            result={"message": f"服务处理异常: {str(e)}"}
        )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=59221, reload=True)