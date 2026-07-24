# -*- coding: utf-8 -*-
"""企业微信群机器人 Webhook 配置"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / ".env")
except ImportError:
    pass

WECOM_BOT_WEBHOOK = os.environ.get("WECOM_BOT_WEBHOOK", "")
WECOM_BOT_NAME = os.environ.get("WECOM_BOT_NAME", "学习监督机器人")
