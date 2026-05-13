# Arete4BUPT · ἀρετή

> 卓越不是天赋，是做出来的。Arete4BUPT 让每个学生都在智能体的引导下走向学术卓越。

## 项目简介

北邮 ACPs 实训营项目。围绕**校园课程场景**，构建一个基于 [ACPs 协议族](https://github.com/AIP-PUB/ACPs-Demo-Project) 的多智能体协作系统。

1 个 **Leader**（个人课程助手）+ 4 个 **Partner**（选课、请假、缓考、考试提醒），通过 AIP 协议互联，接入北邮 ACPs 智能体互联网平台。

## 系统架构

```
用户 (学生)
  │
  ▼
个人课程助手 (Leader, Port 59210)
意图分析 → 任务拆解 → Partner 调度 → 结果整合
  │           │            │            │
  ▼           ▼            ▼            ▼
选课助手     请假助手     缓考助手     考试提醒助手
Port 59221  Port 59222  Port 59223  Port 59224
  │           │            │            │
  └───────────┴────────────┴────────────┘
                    │
          LLM 底座 (Qwen3-8B via vLLM)
          英博云 4090 开发机
```

## 目录结构

```
AreteAgents/
├── leader/                   # Leader Agent（个人课程助手）
│   ├── main.py
│   ├── acs.json
│   ├── config.toml
│   └── prompts.toml
├── partners/
│   ├── course_selector/      # 选课助手
│   ├── leave_request/        # 请假助手
│   ├── exam_deferral/        # 缓考助手
│   └── exam_reminder/        # 考试提醒助手
│       ├── main.py
│       ├── acs.json
│       ├── config.toml
│       └── prompts.toml
├── ACPs_Footprint.py         # 足迹大屏 SDK
├── requirements.txt
└── README.md
```

## 智能体能力矩阵

| Agent | 角色 | 核心能力 |
|-------|------|----------|
| 个人课程助手 | Leader | 意图理解、任务分解、ADP 发现、多 Partner 调度、结果整合 |
| 选课助手 | Partner | 课程查询、方向推荐、先修检查、容量查询、选课规划 |
| 请假助手 | Partner | 请假申请生成、审批流程指引、病假/事假/公假分类、材料清单 |
| 缓考助手 | Partner | 缓考资格判断、材料清单、申请步骤、场景适配 |
| 考试提醒助手 | Partner | 考试时间查询、冲突检测、DDL 提醒、考场信息推送 |

## 技术栈

- **Agent 框架**: Python 3.13+ / FastAPI / Uvicorn
- **LLM**: Qwen3-8B via vLLM（英博云 4090 部署）
- **协议**: ACPs 协议族 (ATR / AIA / ADP / AIP)
- **安全**: mTLS 双向认证
- **可视化**: ACPs Footprint 态势感知大屏
- **协作**: GitHub + GitHub Desktop

## 服务器地址

| 服务 | 地址 |
|------|------|
| Footprint 大屏 | http://117.74.66.90:8006/ |
| 注册服务器 (ATR) | http://117.74.66.90:8002/ |
| 发现服务器 (ADP) | http://117.74.66.90:8005/ |
| 认证服务器 (CA) | http://117.74.66.90:8003/ |

## 组员

| 代号 | 负责 |
|------|------|
| A | Leader + 架构 + 集成 |
| B | 选课助手 |
| C | 请假助手 |
| D | 缓考助手 |
| E | 考试提醒助手 |
| F | GPU + ACPs 基础设施 + 跨组对接 |

## 参考资料

- [ACPs-Demo-Project 旅游助手示例](https://github.com/AIP-PUB/ACPs-Demo-Project)
- [ACPs 参考示例汇总](https://github.com/AIP-PUB/ACPs-Demo-Project/wiki/ACPs-%E5%8F%82%E8%80%83%E7%A4%BA%E4%BE%8B%E6%B1%87%E6%80%BB)
- [英博云 GPU 平台](https://www.ebcloud.com/)
