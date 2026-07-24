# -*- coding: utf-8 -*-
"""全局配置 — WECHAT_MODE 一键切换"""

import os
from pathlib import Path

# 加载 .env 文件
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

# ── 项目路径 ──
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"; DATA_DIR.mkdir(exist_ok=True)

# ── 微信模式 (修改这里一键切换) ──
#   "mock"    → 本地模拟测试
#   "wecom"   → 企业微信官方API (推荐)
#   "weilink" → WeiLink iLink 协议 (仅发消息)
#   "wechaty" → WeChaty + PadLocal (完整双向)
#   "remote"  → 独立设备远程微信服务器
#   "bridge"  → 文件桥接 debug/testing
WECHAT_MODE = os.environ.get("WECHAT_GATEWAY_MODE", "mock")
WECHAT_GATEWAY_MODE = WECHAT_MODE  # alias for main.py

# ── 数据库 ──
DATABASE_PATH = DATA_DIR / "supervisor.db"

# ── 微信网关 ──
WECHAT_GATEWAY_URL = os.environ.get("WECHAT_GATEWAY_URL", "http://localhost:8800")
WECHAT_REMOTE_URL = os.environ.get("WECHAT_REMOTE_URL", "http://192.168.1.100:8700")
WECHAT_GROUP_NAME = os.environ.get("WECHAT_ROOM", "监督")
WECHAT_POLL_INTERVAL = 5

# ── PadLocal (购买后填入) ──
PADLOCAL_TOKEN = os.environ.get("PADLOCAL_TOKEN", "")

# ── DeepSeek API ──
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"

# ── 定时任务 ──
REMINDER_CHECK_INTERVAL_MINUTES = 30
SPOT_CHECK_TIME = "10:00"
SPOT_CHECK_COUNT = 2
STATS_REPORT_TIME = "20:00"
STATS_REPORT_DAY = "mon"

# ── 任务状态 ──
TASK_STATUS_PENDING = "未开始"
TASK_STATUS_IN_PROGRESS = "进行中"
TASK_STATUS_COMPLETED = "已完成"
TASK_STATUS_OVERDUE = "已逾期"

# ── 权限 ──
ADMIN_USERS = os.environ.get("ADMIN_USERS", "").split(",") if os.environ.get("ADMIN_USERS") else []

# ── 日志 ──
LOG_LEVEL = "INFO"
LOG_FILE = DATA_DIR / "bot.log"
