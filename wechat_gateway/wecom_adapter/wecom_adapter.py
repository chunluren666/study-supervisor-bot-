# -*- coding: utf-8 -*-
"""
WeCom Adapter — 企业微信适配器
实现 BaseWechatAdapter 接口，通过企业微信官方 API 收发消息
"""

import time, json, hashlib, logging, threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from .wecom_api import WeComAPI
from .config import WECOM_GROUP_NAME


def _get_process_fn():
    """延迟导入, 避免循环依赖"""
    from task_manager import process_message
    return process_message

LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


class WeComAdapter:
    """
    企业微信适配器 — 兼容 BaseWechatAdapter 接口。
    工作原理:
      企业微信应用 → 群机器人 Webhook 接收消息
      → WeCom API 发送回复
    纯 HTTP API, 零桌面自动化。
    """

    def __init__(self, room_name: str = None):
        self.room = room_name or WECOM_GROUP_NAME
        self.api = WeComAPI()
        self._msg_queue = []
        self._lock = threading.Lock()
        self._online = False
        self._last_msg_hash = None

        self.logger = logging.getLogger("wecom")
        self.logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(LOG_DIR / "wecom.log", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        self.logger.addHandler(fh)

    # ── BaseWechatAdapter 接口 ──

    def start(self):
        """初始化连接 + 启动后台Worker"""
        token = self.api.get_token()
        self._online = bool(token)
        if self._online:
            self.logger.info("WeCom 已连接")
            # 启动后台消息处理器
            from .wecom_worker import MessageWorker
            self._worker = MessageWorker(self, _get_process_fn(), self.send_message)
            self._worker.start()
            self.logger.info("Worker 已启动")
        else:
            self.logger.error("WeCom 连接失败: 请检查 CORP_ID 和 SECRET")

    def get_worker_stats(self) -> dict:
        if hasattr(self, '_worker'):
            return self._worker.stats()
        return {"processed": 0, "failed": 0}

    def stop(self):
        self._online = False

    def receive_message(self) -> Optional[dict]:
        """从消息队列取一条待处理消息"""
        with self._lock:
            if self._msg_queue:
                return self._msg_queue.pop(0)
        return None

    def send_message(self, text: str, room: str = "") -> bool:
        """发送消息到企业微信群"""
        result = self.api.send_text(text, chat_id=room or self.room)
        ok = result.get("errcode") == 0
        if ok:
            self.logger.info(f"已发送: {text[:60]}")
        return ok

    def get_status(self) -> dict:
        return {
            "online": self._online,
            "adapter": "WeComAdapter",
            "room": self.room,
            "protocol": "WeCom Official API",
            "pending": len(self._msg_queue),
        }

    # ── 消息接收（供 Webhook 回调调用） ──

    def on_webhook_message(self, raw_data: dict):
        """
        处理企业微信 Webhook 回调消息。
        外部调用此方法将收到的消息加入队列。
        """
        try:
            # 企业微信回调格式: XML, 解析提取
            msg_type = raw_data.get("MsgType", "")
            if msg_type != "text":
                return

            sender = raw_data.get("From", {}).get("UserId", "未知")
            content = raw_data.get("Text", {}).get("Content", "").strip()
            chat_id = raw_data.get("ChatId", "")
            msg_id = raw_data.get("MsgId", "")

            if not content:
                return

            # 去重
            h = hashlib.md5((str(msg_id) + content).encode()).hexdigest()
            if h == self._last_msg_hash:
                return
            self._last_msg_hash = h

            self.logger.info(f"[{sender}] {content[:100]}")
            with self._lock:
                self._msg_queue.append({
                    "id": f"wc_{msg_id}",
                    "sender": sender,
                    "content": content,
                    "room": chat_id or self.room,
                    "time": datetime.now().isoformat(),
                    "status": "pending",
                })
        except Exception as e:
            self.logger.error(f"Webhook处理失败: {e}")


# ── 工厂注册 ──
def create_wecom_adapter(**kwargs) -> WeComAdapter:
    return WeComAdapter(room_name=kwargs.get("room_name"))
