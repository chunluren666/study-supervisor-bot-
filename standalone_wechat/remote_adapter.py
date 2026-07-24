# -*- coding: utf-8 -*-
"""
Remote Adapter —— 通过 HTTP 与独立微信服务器通信
主电脑的 AI 监督系统用此适配器收发消息
"""

import json, logging, urllib.request, urllib.error, sys, io
from pathlib import Path
from typing import Optional

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


class RemoteWechatAdapter:
    """
    远程微信适配器 —— 实现 BaseWechatAdapter 接口
    通过网络与独立设备上的 wechat_server.py 通信
    """

    def __init__(self, server_url: str = "http://192.168.1.100:8700",
                 room_name: str = "监督"):
        self.url = server_url.rstrip("/")
        self.room = room_name

        self.logger = logging.getLogger("remote_adapter")
        self.logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(LOG_DIR / "remote_adapter.log", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        self.logger.addHandler(fh)

    def _get(self, path):
        try:
            with urllib.request.urlopen(f"{self.url}{path}", timeout=10) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            self.logger.error(f"GET {path}: {e}")
            return {}

    def _post(self, path, data):
        try:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(f"{self.url}{path}", data=body,
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            self.logger.error(f"POST {path}: {e}")
            return {}

    def receive_message(self) -> Optional[dict]:
        result = self._get("/messages")
        msgs = result.get("messages", [])
        return msgs[0] if msgs else None

    def send_message(self, text: str, room: str = "") -> bool:
        result = self._post("/send", {"text": text, "room": room or self.room})
        return result.get("success", False)

    def get_status(self) -> dict:
        result = self._get("/status")
        return {
            "online": result.get("online", False),
            "adapter": "RemoteWechatAdapter",
            "server": self.url,
            "room": self.room,
        }

    def start(self):
        self.logger.info(f"连接远程服务器: {self.url}")

    def stop(self):
        self.logger.info("断开")


# ── 注册到适配器工厂 ──
# 在 wechat_adapter.py 中: create_adapter("remote", server_url="http://...")
