"""主编排器 —— 串联 意图分析→任务拆解→Partner 调用→结果整合."""

import asyncio
import json
import logging
from typing import Optional

from .session import Session, Task, TaskStatus, get_session_manager
from .llm_client import chat, chat_json
from .aip_client import call_partner

logger = logging.getLogger(__name__)


# ── Partner 能力描述（静态版本，后续可从 ADP 动态获取）──
PARTNER_CATALOG = {
    "选课助手": {
        "name": "选课助手",
        "description": "课程查询、方向推荐、先修检查、容量查询、选课方向规划。仅处理校内选课相关。",
        "reject": "校外课程、考研选导、请假/缓考/考试提醒",
    },
    "请假助手": {
        "name": "请假助手",
        "description": "请假申请生成、审批流程指引、材料清单、病假/事假/公假区分。仅处理校内课程请假。",
        "reject": "校外请假、社团请假、选课/缓考/考试提醒",
    },
    "缓考助手": {
        "name": "缓考助手",
        "description": "缓考资格判断、申请步骤指引、材料清单、截止日期。仅处理校内缓考。",
        "reject": "补考/重修、免修申请、选课/请假/考试提醒",
    },
    "考试提醒助手": {
        "name": "考试提醒助手",
        "description": "考试时间查询、冲突检测、考前DDL提醒、考场信息推送。仅处理校内考试。",
        "reject": "非考试日程、补考/重修、选课/请假/缓考",
    },
}

CATALOG_TEXT = "\n".join(
    f"- {p['name']}: {p['description']} （拒绝: {p['reject']}）"
    for p in PARTNER_CATALOG.values()
)


# ═════════════════ 阶段1: 意图分析 ═════════════════

INTENT_SYSTEM = """你是北京邮电大学的学生个人课程助手。你需要分析学生的请求，判断意图类型。

你可以调度的 Partner 智能体如下：
""" + CATALOG_TEXT + """

请输出 JSON：
{
  "intent_type": "选课 / 请假 / 缓考 / 考试提醒 / 混合",
  "confidence": 0.0-1.0,
  "extracted_info": {
    "scenario": "具体场景关键词",
    "urgency": "normal / urgent",
    "keywords": ["关键", "词"]
  },
  "needs_clarification": false,
  "clarification_question": "如果需要追问，写追问内容"
}"""


async def analyze_intent(user_message: str) -> dict:
    """阶段1: 分析用户意图."""
    logger.info("[1/4] 意图分析中...")
    result = chat_json(
        system_prompt=INTENT_SYSTEM,
        user_message=f"学生提问：{user_message}",
        profile="fast",
    )
    logger.info("[1/4] 意图: type=%s confidence=%.2f", result.get("intent_type"), result.get("confidence", 0))
    return result


# ═════════════════ 阶段2: 任务拆解 ═════════════════

PLAN_SYSTEM = """你是任务规划专家。根据意图分析结果，将学生需求拆解为 1-4 个子任务，每个子任务对应一个 Partner。

可用的 Partner（严格遵循，不要编造）：
""" + CATALOG_TEXT + """

请输出 JSON：
{
  "subtasks": [
    {
      "partner_name": "选课助手 / 请假助手 / 缓考助手 / 考试提醒助手",
      "task_description": "用自然语言描述这个子任务，供 Partner 理解",
      "priority": 1-3,
      "depends_on": null 或 前置子任务的 partner_name
    }
  ]
}

要求：
- 每个子任务的 task_description 要具体、可执行，Partner 能直接理解
- 如果一个 Partner 足够处理，返回一个子任务即可
- 混合请求才需要拆到多个 Partner
- priority: 1最高，3最低
- depends_on: 如果有依赖关系填前置 partner_name，没有填 null"""


async def plan_subtasks(intent: dict, user_message: str) -> list[dict]:
    """阶段2: 拆解为子任务."""
    logger.info("[2/4] 任务拆解中...")
    result = chat_json(
        system_prompt=PLAN_SYSTEM,
        user_message=f"原始需求：{user_message}\n意图分析：{json.dumps(intent, ensure_ascii=False)}",
        profile="default",
        max_tokens=3072,
    )
    subtasks = result.get("subtasks", [])
    logger.info("[2/4] 拆解出 %d 个子任务: %s", len(subtasks), [s.get("partner_name") for s in subtasks])
    return subtasks


# ═════════════════ 阶段3: 执行 ═════════════════


async def execute_subtasks(session_id: str, task: Task, subtasks: list[dict]) -> list[dict]:
    """阶段3: 依次调用 Partner，处理依赖关系."""
    logger.info("[3/4] 开始执行 %d 个子任务...", len(subtasks))
    results = []
    done: dict[str, dict] = {}

    for st in subtasks:
        partner = st["partner_name"]
        if partner not in PARTNER_CATALOG:
            results.append({"partner": partner, "error": "未知 Partner"})
            continue

        # 处理依赖
        dep = st.get("depends_on")
        dep_result = None
        if dep and dep in done:
            dep_result = done[dep]

        payload = {
            "message": st["task_description"],
            "original_message": task.results[0].get("intent", {}).get("extracted_info", {}) if task.results else {},
            "depends_on_result": dep_result,
        }

        task.status = TaskStatus.RUNNING
        result = await call_partner(partner, task.id, payload)
        done[partner] = result
        results.append({
            "partner": partner,
            "subtask": st["task_description"],
            "result": result,
        })
        logger.info("[3/4] %s → status=%s", partner, result.get("status", "?"))

    task.results = results
    return results


# ═════════════════ 阶段4: 结果整合 ═════════════════

AGGREGATE_SYSTEM = """你是结果整合专家。你收到了多个 Partner 智能体返回的结果，需要整合成一段自然、完整、对学生有帮助的回复。

规则：
- 如果只有一个 Partner 的结果，浓缩提炼后回复
- 如果有多个 Partner 的结果，按逻辑顺序组织，分段回复
- 如果某个 Partner 返回了错误或拒绝，礼貌地说明原因并建议替代方案
- 不要编造 Partner 没有返回的内容
- 回复语气：温暖、专业的北邮学长风格"""


async def aggregate(session: Session, task: Task, user_message: str) -> str:
    """阶段4: 整合结果."""
    logger.info("[4/4] 结果整合中...")
    results_text = json.dumps([
        {"partner": r["partner"], "subtask": r.get("subtask", ""), "result": r.get("result", {})}
        for r in task.results
    ], ensure_ascii=False, indent=2)

    answer = chat(
        system_prompt=AGGREGATE_SYSTEM,
        user_message=f"原始需求：{user_message}\n\nPartner 返回结果：\n{results_text}",
        profile="pro",
        max_tokens=4096,
    )
    logger.info("[4/4] 整合完成，长度 %d 字", len(answer))
    return answer


# ═════════════════ 主编排入口 ═════════════════

async def orchestrate(session_id: Optional[str], user_message: str) -> dict:
    """从收到用户消息到返回最终结果的主流程."""
    sm = get_session_manager()
    session = sm.get_or_create(session_id)
    task = session.create_task()

    session.history.append({"role": "user", "content": user_message})
    task.status = TaskStatus.RUNNING

    try:
        # 1. 意图分析
        intent = await analyze_intent(user_message)
        task.results.append({"intent": intent})

        # 如果需要追问
        if intent.get("needs_clarification"):
            task.status = TaskStatus.AWAITING_INPUT
            task.clarification = intent.get("clarification_question", "能再详细说下吗？")
            return _build_response(session, task)

        # 2. 任务拆解
        subtasks = await plan_subtasks(intent, user_message)
        task.subtasks = subtasks

        # 3. 执行
        await execute_subtasks(session.id, task, subtasks)

        # 4. 整合
        answer = await aggregate(session, task, user_message)
        task.final_answer = answer
        task.status = TaskStatus.COMPLETED
        session.history.append({"role": "assistant", "content": answer})

        return _build_response(session, task)

    except Exception as e:
        logger.exception("编排失败")
        task.status = TaskStatus.FAILED
        task.final_answer = f"抱歉，处理请求时出现错误：{e}"
        return _build_response(session, task)


def _build_response(session: Session, task: Task) -> dict:
    return {
        "session_id": session.id,
        "active_task_id": session.active_task_id,
        "status": task.status,
        "message": task.final_answer if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
                   else task.clarification or "正在处理...",
        "task_detail": task.to_dict(),
    }
