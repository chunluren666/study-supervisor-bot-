# -*- coding: utf-8 -*-
"""WeiLink 适配器 — 腾讯 iLink 官方协议"""

import time, logging, threading
from datetime import datetime
from pathlib import Path
from typing import Optional

import weilink
from weilink import WeiLink
from weilink.client import Message

from .wechat_adapter import BaseWechatAdapter

LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


class WeiLinkAdapter(BaseWechatAdapter):

    def __init__(self, room_name: str = "监督"):
        self.room = room_name
        self._wl = WeiLink()
        self._msg_queue = []
        self._lock = threading.Lock()
        self._online = False

        self.logger = logging.getLogger("weilink")
        self.logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(LOG_DIR / "weilink.log", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        self.logger.addHandler(fh)

    # ── 接口实现 ──

    def start(self):
        self.logger.info("WeiLink 启动中...")
        try:
            bot = self._wl.login()
            self._online = True
            self.logger.info(f"登录成功: {bot.bot_id}")

            # 注册消息回调
            self._wl.on_message(self._on_message)
            self._wl.run_background()
            self.logger.info("后台运行中")
        except Exception as e:
            self.logger.error(f"启动失败: {e}")

    def stop(self):
        try:
            self._wl.stop()
        except Exception:
            pass
        self._online = False
        self.logger.info("已停止")

    def receive_message(self) -> Optional[dict]:
        with self._lock:
            if self._msg_queue:
                return self._msg_queue.pop(0)
        return None

    def send_message(self, text: str, room: str = "") -> bool:
        try:
            target = room or self.room
            self._wl.send(target, text)
            self.logger.info(f"已发送 → {target}: {text[:60]}")
            return True
        except Exception as e:
            self.logger.error(f"发送失败: {e}")
            return False

    def get_status(self) -> dict:
        return {
            "online": self._online,
            "adapter": "WeiLinkAdapter",
            "room": self.room,
            "protocol": "iLink",
            "pending": len(self._msg_queue),
        }

    # ── 消息回调 ──

    def _on_message(self, msg: Message):
        text = (getattr(msg, 'text', None) or '').strip()
        if not text:
            return
        sender = getattr(msg, 'sender_name', None) or '未知'
        room = getattr(msg, 'chat_name', None) or ''

        self.logger.info(f"[{room}] {sender}: {text[:100]}")
        with self._lock:
            self._msg_queue.append({
                "id": f"wl_{int(time.time())}",
                "sender": sender,
                "content": text,
                "room": room,
                "time": datetime.now().isoformat(),
                "status": "pending",
            })
