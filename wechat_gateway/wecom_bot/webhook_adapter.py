# -*- coding: utf-8 -*-
"""
WeCom Bot Webhook Adapter
企业微信群机器人 — 通过 Webhook URL 发送消息
配置: 群聊 → 群机器人 → 添加 → 复制 Webhook 地址
"""

import json, logging, urllib.request, urllib.error
from pathlib import Path
from typing import Optional
from .config import WECOM_BOT_WEBHOOK

LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


class WeComBotAdapter:
    """企业微信群机器人适配器"""

    def __init__(self, webhook_url: str = None):
        self.url = (webhook_url or WECOM_BOT_WEBHOOK).strip()
        self._online = bool(self.url)
        self._msg_queue = []  # Webhook bot 不能收消息, 保留接口

        self.logger = logging.getLogger("wecom_bot")
        self.logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(LOG_DIR / "wecom_bot.log", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        self.logger.addHandler(fh)

    # ── 接口 ──

    def start(self):
        if not self.url:
            self.logger.error("未配置 WECOM_BOT_WEBHOOK")
            return
        self._online = True
        self.logger.info(f"Webhook Bot 就绪")

    def stop(self):
        self._online = False

    def receive_message(self) -> Optional[dict]:
        """Webhook bot 不支持接收消息, 留给 file_bridge 或 手动输入"""
        return None

    def send_message(self, text: str, room: str = "") -> bool:
        """发送文本消息到群"""
        return self._send({"msgtype": "text", "text": {"content": text}})

    def send_markdown(self, content: str) -> bool:
        """发送 Markdown 消息"""
        return self._send({"msgtype": "markdown", "markdown": {"content": content}})

    def get_status(self) -> dict:
        return {
            "online": self._online,
            "adapter": "WeComBotAdapter",
            "protocol": "WeCom Group Bot Webhook",
        }

    # ── 内部 ──

    def _send(self, body: dict) -> bool:
        if not self.url:
            self.logger.error("Webhook URL 未配置")
            return False
        try:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(self.url, data=data,
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            ok = result.get("errcode") == 0
            if ok:
                text_preview = body.get("text", {}).get("content", "")[:60]
                self.logger.info(f"已发送: {text_preview}")
            else:
                self.logger.error(f"发送失败: {result}")
            return ok
        except Exception as e:
            self.logger.error(f"发送异常: {e}")
            return False


# ── 测试 ──
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    a = WeComBotAdapter()
    print(f"URL: {'已配置' if a.url else '未配置'}")
    if a.url:
        ok = a.send_message(" WeCom Bot 连接测试 - 学习监督机器人已上线")
        print(f"Send: {'OK' if ok else 'FAILED'}")
