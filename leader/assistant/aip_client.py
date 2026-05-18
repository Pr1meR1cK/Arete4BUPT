"""调用 Partner 智能体的 AIP RPC 端点."""

import json
import logging
import httpx

logger = logging.getLogger(__name__)

# Partner 地址映射表
PARTNER_ENDPOINTS: dict[str, str] = {
    "选课助手":   "http://localhost:59221/rpc",
    "请假助手":   "http://localhost:59222/rpc",
    "缓考助手":   "http://localhost:59223/rpc",
    "考试提醒助手": "http://localhost:59224/rpc",
}

TIMEOUT_SECONDS = 120


async def call_partner(partner_name: str, task_id: str, payload: dict) -> dict:
    """向指定 Partner 发送任务，返回结果 dict。"""
    url = PARTNER_ENDPOINTS.get(partner_name)
    if not url:
        return {
            "error": f"未知 Partner: {partner_name}",
            "available": list(PARTNER_ENDPOINTS.keys()),
        }

    body = {
        "task_id": task_id,
        "command": "start",
        "payload": payload,
    }

    logger.info("→ %s  %s", partner_name, url)
    logger.debug("   body: %s", json.dumps(body, ensure_ascii=False)[:200])

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            resp = await client.post(url, json=body)
            resp.raise_for_status()
            result = resp.json()
            logger.info("← %s  status=%s", partner_name, result.get("status", "?"))
            return result
    except httpx.TimeoutException:
        logger.warning("← %s  timeout", partner_name)
        return {"error": f"{partner_name} 请求超时", "status": "failed"}
    except Exception as e:
        logger.warning("← %s  error: %s", partner_name, e)
        return {"error": str(e), "status": "failed"}
