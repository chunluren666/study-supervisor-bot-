# -*- coding: utf-8 -*-
"""企业微信群机器人 Webhook — 纯发送, 不读取消息"""

import json, logging, urllib.request, urllib.error
from .config import WECOM_GROUP_WEBHOOK_URL

log = logging.getLogger("group_bot")


class GroupBot:
    """企业微信群机器人"""

    def __init__(self, webhook_url: str = None):
        self.url = (webhook_url or WECOM_GROUP_WEBHOOK_URL).strip()

    def _post(self, body: dict) -> bool:
        if not self.url:
            log.warning("Webhook URL 未配置")
            return False
        try:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(self.url, data=data,
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                r = json.loads(resp.read().decode("utf-8"))
            ok = r.get("errcode") == 0
            if ok: log.info(f"群发成功")
            else: log.error(f"群发失败: {r}")
            return ok
        except Exception as e:
            log.error(f"群发异常: {e}")
            return False

    def send_text(self, content: str) -> bool:
        return self._post({"msgtype": "text", "text": {"content": content}})

    def send_markdown(self, content: str) -> bool:
        return self._post({"msgtype": "markdown", "markdown": {"content": content}})

    def send_task_notice(self, title: str, detail: str) -> bool:
        """任务发布通知"""
        return self.send_markdown(f"## 新任务\n**{title}**\n{detail}")

    def send_reminder(self, msg: str) -> bool:
        return self.send_text(f" {msg}")

    def send_daily_report(self, report: str) -> bool:
        return self.send_markdown(f"## 每日学习报告\n{report}")

    def send_weekly_report(self, report: str) -> bool:
        return self.send_markdown(f"## 本周学习报告\n{report}")
