# -*- coding: utf-8 -*-
"""群机器人适配器 — 统一接口, 对接 scheduler 和 report_generator"""

import logging
from pathlib import Path
from .webhook_bot import GroupBot
from .config import WECOM_GROUP_WEBHOOK_URL

LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


class GroupBotAdapter:
    """群机器人适配器 — 只发不收"""

    def __init__(self):
        self.bot = GroupBot(WECOM_GROUP_WEBHOOK_URL)
        self._online = bool(WECOM_GROUP_WEBHOOK_URL)

        self.logger = logging.getLogger("group_bot_adapter")
        self.logger.setLevel(logging.INFO)
        fh = logging.FileHandler(LOG_DIR / "group_bot.log", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        self.logger.addHandler(fh)

    def send(self, text: str) -> bool:
        if not self._online:
            self.logger.warning("群机器人未配置")
            return False
        return self.bot.send_text(text)

    def send_report(self, report: str) -> bool:
        return self.bot.send_markdown(report)

    def send_reminder(self, msg: str) -> bool:
        return self.bot.send_reminder(msg)

    def broadcast(self, title: str, content: str) -> bool:
        return self.bot.send_markdown(f"## {title}\n{content}")

    @property
    def online(self) -> bool:
        return self._online
