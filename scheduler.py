# -*- coding: utf-8 -*-
"""
定时任务——提醒、抽查、统计汇报
"""

import random
import time
import threading
from datetime import datetime
from database import (
    init_db, list_members, get_pending_tasks, get_tasks_by_member,
    update_task_status, add_reminder, create_spot_check,
)
from task_manager import (
    generate_reminders, do_spot_check, generate_stats_report,
)
from config import (
    REMINDER_CHECK_INTERVAL_MINUTES, SPOT_CHECK_TIME,
    SPOT_CHECK_COUNT, STATS_REPORT_TIME, STATS_REPORT_DAY,
)


class Scheduler:
    """轻量级调度器，在线程中运行，不依赖外部服务"""

    def __init__(self, on_send_message, on_group_broadcast=None):
        """
        on_send_message: 回调函数，用于发送私聊消息
        on_group_broadcast: 群广播回调 (可选)
        """
        self.on_send = on_send_message
        self.on_broadcast = on_group_broadcast
        self.running = False
        self.thread = None
        self._last_reminder_check = None
        self._last_spot_check = None
        self._last_stats_report = None
        self._last_backup = None
        self._last_rotate = None
        self._last_plan_morning = None
        self._last_plan_afternoon = None
        self._last_plan_evening = None

    def start(self):
        """启动调度器（后台线程）"""
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        print("[Scheduler] 定时任务已启动")

    def stop(self):
        """停止调度器"""
        self.running = False
        print("[Scheduler] 定时任务已停止")

    def _loop(self):
        """主循环，每分钟检查一次"""
        # 启动后等30秒再开始
        time.sleep(30)
        while self.running:
            now = datetime.now()
            today = now.strftime("%Y-%m-%d")
            current_time = now.strftime("%H:%M")

            # ── 0. 每日计划提醒 ──
            if current_time == "08:00" and self._last_plan_morning != today:
                self._last_plan_morning = today
                self._plan_reminder("morning")
            if current_time == "14:00" and self._last_plan_afternoon != today:
                self._last_plan_afternoon = today
                self._plan_reminder("afternoon")
            if current_time == "21:00" and self._last_plan_evening != today:
                self._last_plan_evening = today
                self._plan_reminder("evening")

            # ── 1. 每日备份(凌晨3点) ──
            if current_time == "03:00" and self._last_backup != today:
                self._last_backup = today
                self._do_backup()

            # ── 1. 到期提醒 ──
            if (self._last_reminder_check is None or
                    (now - self._last_reminder_check).total_seconds() >=
                    REMINDER_CHECK_INTERVAL_MINUTES * 60):
                self._last_reminder_check = now
                self._check_reminders()

            # ── 2. 每日抽查 ──
            if current_time >= SPOT_CHECK_TIME and self._last_spot_check != today:
                self._last_spot_check = today
                self._do_spot_checks()

            # ── 3. 统计汇报 ──
            if current_time >= STATS_REPORT_TIME and self._last_stats_report != today:
                if STATS_REPORT_DAY == "mon" and now.weekday() == 0:
                    self._last_stats_report = today
                    self._do_stats_report()
                elif STATS_REPORT_DAY == "fri" and now.weekday() == 4:
                    self._last_stats_report = today
                    self._do_stats_report()
                elif STATS_REPORT_DAY == "daily":
                    self._last_stats_report = today
                    self._do_stats_report()

            # ── 4. 日志轮转(凌晨4点) ──
            if current_time == "04:00" and self._last_rotate != today:
                self._last_rotate = today
                self._do_log_rotate()

            time.sleep(60)

    # ── 内部方法 ──

    def _check_reminders(self):
        """检查并发送提醒"""
        reminders = generate_reminders()
        if not reminders:
            return

        from risk_analyzer import get_reminder_strategy, get_latest_risk, RISK_HIGH, RISK_MEDIUM

        for task_id, member_id, message in reminders:
            add_reminder(task_id, member_id, "auto_reminder", message)

            if member_id:
                risk = get_latest_risk(member_id)
                risk_level = risk.get("risk_level", "low") if risk else "low"

                if risk_level == RISK_HIGH:
                    message = f"[HIGH RISK] {message}"
                elif risk_level == RISK_MEDIUM:
                    message = f"[!] {message}"

            self.on_send(message)
            # 群广播提醒
            if self.on_broadcast:
                self.on_broadcast(f" 提醒通知\n{message}")
            print(f"[Scheduler] 提醒: {message[:60]}")

    def _do_spot_checks(self):
        """智能抽查 —— 优先高风险成员"""
        from check_manager import do_smart_spot_check
        import random as _random

        members = list_members()
        if not members:
            return

        # 优先使用智能抽查
        try:
            messages = do_smart_spot_check(SPOT_CHECK_COUNT)
            for msg in messages:
                if msg:
                    self.on_send(msg)
                    time.sleep(2)
        except Exception as e:
            print(f"[Scheduler] 智能抽查失败, 回退随机: {e}")
            targets = _random.sample(members, min(SPOT_CHECK_COUNT, len(members)))
            for m in targets:
                msg = do_spot_check(m["wx_name"], m["id"])
                if msg:
                    self.on_send(msg)
                time.sleep(2)

    def _do_stats_report(self):
        """发送统计报告"""
        report = generate_stats_report()
        if report and report.strip():
            self.on_send(report)
            if self.on_broadcast:
                self.on_broadcast(f"## 学习统计\n{report}")
            print(f"[Scheduler] 统计报告已发送")

    def _do_backup(self):
        try:
            from database import backup_database
            path = backup_database()
            print(f"[Scheduler] 备份: {path}")
        except Exception as e:
            print(f"[Scheduler] 备份失败: {e}")

    def _plan_reminder(self, phase: str):
        """每日计划提醒: morning/afternoon/evening"""
        msgs = {
            "morning": " 早上好！请提交今日学习计划。格式:\n今天要完成: [学科] [内容] [数量]",
            "afternoon": " 下午好！请检查进度:\n1. 上午完成了什么?\n2. 下午计划是什么?\n3. 遇到什么困难?",
            "evening": " 晚上好！请提交今日学习总结:\n完成的每项任务 + 未完成的原因",
        }
        msg = msgs.get(phase, "")
        if msg:
            self.on_send(msg)
            print(f"[Plan] {phase} 提醒")

    def _do_log_rotate(self):
        try:
            from logs.rotate import rotate
            rotate()
        except Exception as e:
            print(f"[Scheduler] 日志轮转失败: {e}")

    # ── 手动触发 ──

    def trigger_reminder_check(self):
        """手动触发提醒检查"""
        self._check_reminders()

    def trigger_spot_check(self):
        """手动触发抽查"""
        self._do_spot_checks()

    def trigger_stats_report(self):
        """手动发送统计报告"""
        self._do_stats_report()


# ── 测试 ──
if __name__ == "__main__":
    init_db()

    def fake_send(msg):
        print(f"[发送] {msg}")

    s = Scheduler(fake_send)
    print("手动触发提醒...")
    s.trigger_reminder_check()
    print("\n手动触发抽查...")
    s.trigger_spot_check()
    print("\n手动触发统计...")
    s.trigger_stats_report()
