# -*- coding: utf-8 -*-
"""每日计划监督 — 解析/追踪/审核全天学习"""

import json, time, re, logging
from datetime import datetime, date
from database import get_db

log = logging.getLogger("daily_plan")


# ── 计划解析 ──

PLAN_PARSE_PROMPT = """你是一个考研监督老师。学生提交了今日学习计划，请解析为结构化任务。

学生计划: {message}

提取每个任务:
{"tasks":[{"subject":"学科","content":"内容","target_count":"数量","estimated_minutes":分钟,"priority":"high|medium|low"}],
 "total_estimated_hours":总估计小时}

只返回JSON。"""


def parse_daily_plan(message: str) -> dict:
    """解析每日计划 → 结构化任务列表"""
    from ai import _call_deepseek
    prompt = PLAN_PARSE_PROMPT.format(message=message)
    result = _call_deepseek("严格的考研监督老师。只返回JSON。", prompt, temperature=0.2)
    try:
        if "```" in result: result = result.split("```")[1].replace("json", "", 1)
        return json.loads(result.strip())
    except json.JSONDecodeError:
        return {"tasks": [{"subject": "未分类", "content": message, "target_count": "?", "estimated_minutes": 0, "priority": "medium"}], "total_estimated_hours": 0}


# ── 数据库 ──

def create_daily_plan(user_id: str, raw_message: str) -> dict:
    """保存每日计划，返回计划ID和任务列表"""
    parsed = parse_daily_plan(raw_message)
    tasks = parsed.get("tasks", [])
    today = date.today().isoformat()

    db = get_db()
    db.execute("INSERT INTO daily_plans (user_id, date, raw_message, total_hours) VALUES (?, ?, ?, ?)",
               (user_id, today, raw_message, parsed.get("total_estimated_hours", 0)))
    plan_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    for t in tasks:
        db.execute(
            "INSERT INTO daily_tasks (plan_id, user_id, subject, content, target_count, estimated_minutes, priority) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (plan_id, user_id, t.get("subject", ""), t.get("content", ""),
             t.get("target_count", ""), t.get("estimated_minutes", 0),
             t.get("priority", "medium"))
        )
    db.commit()
    db.close()
    return {"plan_id": plan_id, "tasks": tasks, "total_hours": parsed.get("total_estimated_hours", 0)}


def update_task_progress(task_id: int, status: str, actual_count: str = "",
                         actual_minutes: int = 0, note: str = ""):
    """更新任务完成状态"""
    db = get_db()
    completed_at = datetime.now().isoformat() if status == "completed" else None
    db.execute(
        "UPDATE daily_tasks SET status=?, actual_count=?, actual_minutes=?, note=?, completed_at=? WHERE id=?",
        (status, actual_count, actual_minutes, note, completed_at, task_id)
    )
    db.commit()
    db.close()


def get_today_plan(user_id: str) -> dict:
    """获取今日计划及任务"""
    today = date.today().isoformat()
    db = get_db()
    plan = db.execute("SELECT * FROM daily_plans WHERE user_id=? AND date=? ORDER BY id DESC LIMIT 1",
                      (user_id, today)).fetchone()
    if not plan:
        db.close()
        return {}
    tasks = db.execute("SELECT * FROM daily_tasks WHERE plan_id=? ORDER BY priority, id",
                       (plan["id"],)).fetchall()
    db.close()
    return {"plan": dict(plan), "tasks": [dict(t) for t in tasks]}


def get_daily_summary(user_id: str) -> str:
    """生成每日摘要"""
    plan = get_today_plan(user_id)
    if not plan:
        return "今日无计划。"

    tasks = plan["tasks"]
    completed = [t for t in tasks if t["status"] == "completed"]
    in_progress = [t for t in tasks if t["status"] == "in_progress"]
    pending = [t for t in tasks if t["status"] == "pending"]

    lines = [" 今日学习总结", ""]
    lines.append(f"计划: {len(tasks)} 项 | 完成: {len(completed)} | 进行中: {len(in_progress)} | 未开始: {len(pending)}")

    if completed:
        lines.append("\n 已完成:")
        for t in completed:
            lines.append(f"  {t['subject']}: {t['content']} ({t.get('actual_count', t['target_count'])})")

    if pending:
        lines.append(f"\n 未完成 ({len(pending)}项):")
        for t in pending:
            lines.append(f"  {t['subject']}: {t['content']}")

    return "\n".join(lines)


# ── 计划回复 ──

def format_plan_reply(plan_data: dict) -> str:
    """格式化计划确认回复"""
    tasks = plan_data.get("tasks", [])
    lines = [" 今日计划已记录:", ""]
    for i, t in enumerate(tasks, 1):
        subj = t.get("subject", "")
        content = t.get("content", "")
        count = t.get("target_count", "")
        mins = t.get("estimated_minutes", 0)
        prio = {"high": "", "medium": "", "low": ""}.get(t.get("priority", ""), "")
        lines.append(f"{i}. {prio} {subj}: {content}")
        if count: lines[-1] += f" ({count})"
        if mins: lines[-1] += f" [{mins}min]"

    lines.append(f"\n共 {len(tasks)} 项, 估计 {plan_data.get('total_hours', 0)}h")
    lines.append("\n完成后请汇报: 完成 [序号] [具体结果]")
    return "\n".join(lines)


# ── 检测是否计划消息 ──

def is_daily_plan_message(msg: str) -> bool:
    """判断消息是否为每日计划"""
    plan_keywords = ["今天要", "今日计划", "今天完成", "今天做", "今天任务",
                     "今天学习", "今天复习", "今天的计划", "今天安排"]
    return any(kw in msg for kw in plan_keywords)
