# 学习监督机器人 v2.0

AI 驱动的微信群学习监督助手。自动记录任务、审核完成情况、风险分析、定时提醒、随机抽查、生成学习报告。

## 功能

- **任务管理** — 老师发布任务 → AI 自动解析 → 分配给成员
- **完成审核** — 学生提交完成 → AI 判断证据充分性 → 通过/驳回
- **证据机制** — 文字/图片/文件证据，状态流转：pending→submitted→approved/rejected
- **学习评分** — 固定权重：完成率40% + 及时率30% + 质量30%
- **风险分析** — 逾期/低完成/评分下降 → low/medium/high
- **智能抽查** — 按风险等级优先选择目标，个性化问题
- **定时提醒** — 截止前24h提醒，逾期警告，风险等级调整频率
- **周报/月报** — 个人报告 + 群组统计
- **角色权限** — student/teacher/admin 三级权限
- **Web 仪表盘** — 任务/审核/评分/风险可视化

## 安装

```bash
# Python 3.10+
pip install fastapi uvicorn apscheduler

# 可选: WeiLink 微信接入
pip install weilink
```

## 配置

编辑 `.env`:

```ini
DEEPSEEK_API_KEY=sk-xxxx          # DeepSeek API Key
WECHAT_MODE=mock                   # mock | weilink | wechaty
WECHAT_ROOM=监督                   # 监听群名
ADMIN_USERS=王老师                  # 管理员
```

## 启动

```bash
# 一键启动
start.bat

# 或手动:
python main.py              # Mock 测试模式
python main.py --web        # Web 仪表盘 (localhost:8000)
python main.py --add-msg    # 交互添加消息
```

## 微信接入

| 模式 | 说明 | 费用 |
|------|------|------|
| `mock` | 预设消息测试 | 免费 |
| `weilink` | iLink 协议(仅发) | 免费 |
| `wechaty` | PadLocal 完整双向 | ~$30/年 |

详见 `wechat_gateway/ADAPTERS.md`

## 测试

```bash
python -m tests.test_task_flow       # 任务流程测试(3场景)
python -m tests.test_supervision     # 监督策略测试(5场景)
```

## 项目结构

```
study-supervisor-bot/
├── main.py                 # 入口
├── config.py               # 配置
├── database.py             # SQLite + CRUD
├── ai.py                   # DeepSeek API
├── task_manager.py         # 消息路由 + 任务管理
├── scheduler.py            # 定时提醒/抽查
├── risk_analyzer.py        # 风险分析
├── check_manager.py        # 智能抽查
├── study_score.py          # 学习评分
├── report_generator.py     # 周报/月报
├── wechat_gateway/         # 微信适配器
│   ├── python_adapter/     # Mock/WeiLink/WeChaty
│   └── node_service/       # WeChaty 网关
├── tests/                  # 测试套件
├── templates/              # Web 仪表盘
├── logs/                   # 运行日志
└── backups/                # 数据库备份
```
