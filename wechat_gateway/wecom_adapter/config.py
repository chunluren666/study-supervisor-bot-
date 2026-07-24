# -*- coding: utf-8 -*-
"""企业微信适配器配置"""

import os
from pathlib import Path

# 确保加载 .env
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / ".env")
except ImportError:
    pass

WECOM_CORP_ID = os.environ.get("WECOM_CORP_ID", "")
WECOM_SECRET = os.environ.get("WECOM_SECRET", "")
WECOM_AGENT_ID = int(os.environ.get("WECOM_AGENT_ID", "0") or "0")
WECOM_TOKEN = os.environ.get("WECOM_TOKEN", "")        # 回调验证
WECOM_ENCODING_AES_KEY = os.environ.get("WECOM_AES_KEY", "") or os.environ.get("WECOM_ENCODING_AES_KEY", "")

# 企业微信API
WECOM_API_BASE = "https://qyapi.weixin.qq.com/cgi-bin"
WECOM_GROUP_NAME = os.environ.get("WECHAT_ROOM", "监督")

# ── 生产部署 ──
WECOM_PUBLIC_URL = os.environ.get("WECOM_PUBLIC_URL", "")           # https://your-domain.com
WECOM_CALLBACK_PATH = "/wecom/callback"                              # 回调路径
WECOM_DEPLOY_MODE = os.environ.get("WECOM_DEPLOY_MODE", "local")    # local | production
