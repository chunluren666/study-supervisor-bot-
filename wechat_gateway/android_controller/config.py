# -*- coding: utf-8 -*-
"""Android 微信控制器 — 配置"""

import os

# ADB 连接方式: "usb" | "wifi"
ADB_MODE = os.environ.get("ADB_MODE", "usb")
WIFI_DEVICE_IP = os.environ.get("ANDROID_IP", "192.168.1.x")

# 微信
WECHAT_PACKAGE = "com.tencent.mm"
TARGET_GROUP = os.environ.get("WECHAT_ROOM", "监督")

# HTTP 服务
SERVER_PORT = int(os.environ.get("WECHAT_SERVER_PORT", "8700"))

# 发送频率限制: N秒内最多M条
RATE_LIMIT_SECONDS = 60
RATE_LIMIT_MAX = 3

# 轮询间隔(秒)
POLL_INTERVAL = 5

# 日志
LOG_LEVEL = "INFO"
