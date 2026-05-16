import requests
import json

url = "http://localhost:59221/rpc"
headers = {"Content-Type": "application/json"}

# 测试用例 1：合法请求（测试 Decision 通过 + Analysis + Production）
payload_valid = {
    "task_id": "001",
    "command": "start",
    "payload": {
        "message": "推荐AI方向的选修课，我有Python基础"
    }
}

# 测试用例 2：非法请求（测试 Decision 拒绝）
payload_invalid = {
    "task_id": "002",
    "command": "start",
    "payload": {
        "message": "我要请假三天"
    }
}

print("===== 测试 1：合法请求 =====")
try:
    resp = requests.post(url, json=payload_valid, headers=headers)
    print("Status:", resp.status_code)
    print("Response:", json.dumps(resp.json(), indent=2, ensure_ascii=False))
except Exception as e:
    print("Error:", e)

print("\n===== 测试 2：非法请求 =====")
try:
    resp = requests.post(url, json=payload_invalid, headers=headers)
    print("Status:", resp.status_code)
    print("Response:", json.dumps(resp.json(), indent=2, ensure_ascii=False))
except Exception as e:
    print("Error:", e)