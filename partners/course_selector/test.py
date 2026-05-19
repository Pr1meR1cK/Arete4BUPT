"""Arete4BUPT 选课助手 — 测试脚本（严格对齐 Partner 交付标准）"""
import json
import requests

BASE_URL = "http://localhost:59221"


TEST_CASES = [
    # ===== 一、基础能力验证 =====
    {
        "name": "TC1: 信息不全的选课请求 → awaiting_input",
        "payload": {
            "task_id": "tc001",
            "command": "start",
            "payload": {
                "message": "帮我选一门AI方向的选修课",
                "original_message": {
                    "scenario": "选课",
                    "urgency": "normal",
                    "keywords": ["AI", "选修"]
                },
                "depends_on_result": None
            }
        },
        "expect_status": "awaiting_input"
    },
    {
        "name": "TC2: 信息完整的选课请求 → completed",
        "payload": {
            "task_id": "tc002",
            "command": "start",
            "payload": {
                "message": "帮我选一门AI方向的选修课，我是大二计算机学院的",
                "original_message": {
                    "scenario": "选课",
                    "urgency": "normal",
                    "keywords": ["AI", "选修", "大二", "计算机学院"]
                },
                "depends_on_result": None
            }
        },
        "expect_status": "completed"
    },

    # ===== 二、边界 & 拒绝场景 =====
    {
        "name": "TC3: 完全超出服务范围（请假） → failed",
        "payload": {
            "task_id": "tc003",
            "command": "start",
            "payload": {
                "message": "我想请3天病假，需要准备什么材料",
                "original_message": {
                    "scenario": "请假",
                    "urgency": "normal",
                    "keywords": ["病假", "材料"]
                },
                "depends_on_result": None
            }
        },
        "expect_status": "failed"
    },
    {
        "name": "TC4: 混合请求（选课 + 请假） → completed 或 failed（允许两种实现）",
        "payload": {
            "task_id": "tc004",
            "command": "start",
            "payload": {
                "message": "帮我选一门AI课，顺便帮我请个假",
                "original_message": {
                    "scenario": "混合",
                    "urgency": "normal",
                    "keywords": ["AI课", "请假"]
                },
                "depends_on_result": None
            }
        },
        "expect_status": ["completed", "failed"]
    },
    {
        "name": "TC5: 空消息请求 → failed",
        "payload": {
            "task_id": "tc005",
            "command": "start",
            "payload": {
                "message": "",
                "original_message": {},
                "depends_on_result": None
            }
        },
        "expect_status": "failed"
    },

    # ===== 三、三阶段流程完整性校验 =====
    {
        "name": "TC6: 先修检查请求 → completed",
        "payload": {
            "task_id": "tc006",
            "command": "start",
            "payload": {
                "message": "选计算机视觉需要先修什么课",
                "original_message": {
                    "scenario": "选课",
                    "urgency": "normal",
                    "keywords": ["计算机视觉", "先修"]
                },
                "depends_on_result": None
            }
        },
        "expect_status": "completed"
    },
    {
        "name": "TC7: 容量查询请求 → completed",
        "payload": {
            "task_id": "tc007",
            "command": "start",
            "payload": {
                "message": "计算机视觉这门课还有名额吗",
                "original_message": {
                    "scenario": "选课",
                    "urgency": "normal",
                    "keywords": ["计算机视觉", "名额"]
                },
                "depends_on_result": None
            }
        },
        "expect_status": "completed"
    },

    # ===== 四、返回结构规范校验 =====
    {
        "name": "TC8: 返回结构必须包含 task_id / status / result.message",
        "payload": {
            "task_id": "tc008",
            "command": "start",
            "payload": {
                "message": "帮我看看大三有什么AI相关的必修课",
                "original_message": {
                    "scenario": "选课",
                    "urgency": "normal",
                    "keywords": ["大三", "AI", "必修"]
                },
                "depends_on_result": None
            }
        },
        "expect_status": "completed",
        "check_structure": True
    }
]


def test_health():
    print("=" * 70)
    print("测试 0: 健康检查 GET /health")
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        assert r.status_code == 200
        body = r.json()
        assert body.get("status") == "ok"
        assert body.get("agent") == "选课助手"
        print("✅ 通过 |", body)
    except Exception as e:
        print("❌ 失败 |", e)
    print()


def run_case(case):
    print("-" * 70)
    print("测试用例:", case["name"])
    print("期望状态:", case["expect_status"])

    try:
        r = requests.post(
            f"{BASE_URL}/rpc",
            json=case["payload"],
            headers={"Content-Type": "application/json"},
            timeout=90
        )

        # 交付标准要求：不抛 500，始终返回 JSON
        data = r.json()
        status = data.get("status")
        expects = case["expect_status"]

        # 状态判断
        if isinstance(expects, list):
            ok = status in expects
        else:
            ok = status == expects

        print(f"{'✅ 通过' if ok else '❌ 失败'} | 实际状态: {status}")

        # 结构校验（TC8）
        if case.get("check_structure"):
            assert "task_id" in data, "缺少 task_id"
            assert data["task_id"] == case["payload"]["task_id"], "task_id 不一致"
            assert "status" in data, "缺少 status"
            assert "result" in data and "message" in data["result"], "缺少 result.message"
            print("✅ 返回结构符合交付标准")

        print("返回内容:")
        print(json.dumps(data, ensure_ascii=False, indent=2))

    except Exception as e:
        print("❌ 请求或断言失败 |", e)

    print()


def main():
    print("=" * 70)
    print("Arete4BUPT 选课助手 标准化测试")
    print("=" * 70)
    print()

    test_health()

    for case in TEST_CASES:
        run_case(case)

    print("=" * 70)
    print("测试完成")
    print("=" * 70)


if __name__ == "__main__":
    main()