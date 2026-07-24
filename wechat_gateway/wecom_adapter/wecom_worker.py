# -*- coding: utf-8 -*-
"""后台消息 Worker — 异步处理队列, 避免阻塞回调"""

import time, threading, logging
from datetime import datetime

log = logging.getLogger("wecom_worker")


class MessageWorker:
    """后台消息处理器"""

    def __init__(self, adapter, process_fn, send_fn):
        """
        adapter: WeComAdapter 实例
        process_fn: task_manager.process_message
        send_fn: adapter.send_message
        """
        self.adapter = adapter
        self.process = process_fn
        self.send = send_fn
        self.running = False
        self._processed = 0
        self._failed = 0
        self._last_latency = 0

    def start(self):
        self.running = True
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()
        log.info("Worker 已启动")

    def stop(self):
        self.running = False

    def stats(self) -> dict:
        return {
            "processed": self._processed,
            "failed": self._failed,
            "last_latency_ms": self._last_latency,
            "queue_size": len(self.adapter._msg_queue) if hasattr(self.adapter, '_msg_queue') else 0,
        }

    def _loop(self):
        while self.running:
            try:
                msg = self.adapter.receive_message()
                if not msg:
                    time.sleep(0.5)
                    continue

                sender = msg.get("sender", "")
                content = msg.get("content", "")
                t0 = time.time()

                # 管理员命令
                cmd_result = _handle_command(content, sender)
                if cmd_result:
                    self.send(cmd_result, msg.get("room", ""))
                    self._processed += 1
                    self._last_latency = int((time.time() - t0) * 1000)
                    continue

                # 正常消息流
                try:
                    reply = self.process(sender, content)
                    if reply:
                        self.send(reply, msg.get("room", ""))
                    self._processed += 1
                except Exception as e:
                    self._failed += 1
                    log.error(f"处理失败 [{sender}]: {e}")

                self._last_latency = int((time.time() - t0) * 1000)

            except Exception as e:
                log.error(f"Worker异常: {e}")
                time.sleep(1)


# ── 管理员命令系统 ──

def _handle_command(content: str, sender: str) -> str:
    """处理 /命令"""
    if not content.startswith("/"):
        return ""

    from database import is_teacher_or_admin
    if not is_teacher_or_admin(sender):
        return f"@{sender} 只有老师/管理员可使用命令"

    cmd = content.split()[0].lower()

    if cmd == "/发布任务":
        return "请直接发送任务内容, 格式: 完成XX任务, 截止XX, 成员XX负责"

    if cmd == "/查看排名":
        from study_score import get_leaderboard
        lb = get_leaderboard()
        lines = [" 学习排名:"]
        for i, s in enumerate(lb[:5], 1):
            lines.append(f"{i}. {s.get('member_name','?')} {s.get('overall_score',0):.0f}分")
        return "\n".join(lines)

    if cmd == "/查看风险":
        from risk_analyzer import assess_all
        risks = assess_all()
        lines = [" 风险概览:"]
        for r in risks:
            emoji = {"low":"","medium":"","high":""}.get(r["risk_level"],"")
            lines.append(f"{emoji} {r.get('member_name','?')}: {r['risk_level']} ({r.get('detail','')})")
        return "\n".join(lines)

    if cmd == "/生成周报":
        from report_generator import generate_group_report
        return generate_group_report("weekly")

    if cmd == "/帮助":
        return "命令: /发布任务 /查看排名 /查看风险 /生成周报"

    return f"未知命令: {cmd}。输入 /帮助 查看可用命令"
