# -*- coding: utf-8 -*-
"""
任务管理器——消息路由、任务生命周期、完成处理
"""

import hashlib
from datetime import datetime
from database import (
    init_db, ensure_member, create_task, get_pending_tasks,
    get_tasks_by_member, update_task_status, complete_task,
    log_message, is_duplicate_message, get_all_stats,
    create_spot_check, answer_spot_check, add_reminder,
)
from ai import parse_task_message, check_completion, evaluate_spot_check


# ── 消息路由 ──

def process_message(sender: str, content: str, is_group: bool = True) -> str:
    # ── 每日计划检测 ──
    from daily_plan_manager import is_daily_plan_message, create_daily_plan, format_plan_reply
    if is_daily_plan_message(content):
        try:
            plan = create_daily_plan(sender, content)
            return format_plan_reply(plan)
        except Exception as e:
            pass  # fall through to normal processing
    """
    处理一条微信群消息，返回机器人应回复的内容。
    这是核心入口函数，所有消息都经过此路由。
    """
    # 去重
    msg_hash = hashlib.md5(content.strip().encode()).hexdigest()
    if is_duplicate_message(msg_hash):
        return ""

    log_message(msg_hash, sender, content)

    # 路由判断
    result = parse_task_message(content)

    intent = result.get("intent", "unknown")

    if intent == "task_publish":
        return _handle_task_publish(sender, result)

    elif intent == "task_complete":
        return _handle_task_complete(sender, content)

    else:
        # 非结构化消息，尝试匹配"完成"关键词
        if _looks_like_completion(content):
            return _handle_task_complete(sender, content)
        # 其他消息尝试通用对话
        if content.strip():
            return _handle_general_chat(sender, content)

    return ""


# ── 任务发布处理 ──

def _stats_hook(msg_type: str, result: dict = None):
    """统计钩子 — 不影响业务逻辑"""
    try:
        from runtime_stats import task_created, ai_check
        if msg_type == "task": task_created()
        elif msg_type == "ai" and result:
            ai_check(result.get("decision", ""))
    except Exception:
        pass


def _handle_task_publish(sender: str, parsed: dict) -> str:
    """处理任务发布消息 —— 仅 teacher/admin 可发布"""
    from database import can_publish_task
    if not can_publish_task(sender):
        return f"@{sender} 只有老师或管理员可以发布任务"

    title = parsed.get("title", "新任务")
    content = parsed.get("content", "")
    deadline = parsed.get("deadline")
    assignees = parsed.get("assignees", [])

    task_id = create_task(
        title=title,
        content=content,
        deadline=deadline,
        publisher_name=sender,
        assignee_names=assignees,
    )
    _stats_hook("task")

    # 构建回复
    reply = f" 已记录新任务：{title}\n"
    if deadline:
        reply += f" 截止时间：{deadline}\n"
    if assignees:
        reply += f" 负责人：{', '.join(assignees)}\n"
    reply += f"\n请相关成员在完成后在群里回复「完成 {title}」或说明具体完成情况。"

    return reply


# ── 任务完成处理 ──

def _handle_task_complete(sender: str, content: str) -> str:
    """
    处理成员完成任务的消息。
    状态流转: pending → submitted → (AI审核) → approved/rejected
    """
    tasks = get_tasks_by_member(sender)

    if not tasks:
        return f"@{sender} 你当前没有待完成的任务~"

    # 尝试匹配具体任务
    matched_task = None
    for t in tasks:
        if t["title"] in content:
            matched_task = t
            break

    if not matched_task:
        matched_task = tasks[0]

    # 1. 先提交证据（状态: pending → submitted）
    from database import (
        get_assignee_by_task_and_member, submit_evidence,
        audit_evidence, STATUS_APPROVED, STATUS_REJECTED,
    )
    assignee = get_assignee_by_task_and_member(matched_task["id"], sender)
    if not assignee:
        return f"@{sender} 未找到你的任务分配记录"

    evidence_id = submit_evidence(
        assignee["id"],
        evidence_type="text",
        text_content=content,
    )

    # 2. AI 审核证据
    ai_result = check_completion(
        matched_task.get("content", ""),
        content,
    )
    decision = ai_result.get("decision", "need_more")
    reason = ai_result.get("reason", "")
    quality = ai_result.get("quality", "ok")

    # 3. 记录审核结果并更新状态
    audit_evidence(assignee["id"], evidence_id, decision, reason)
    _stats_hook("ai", ai_result)

    if decision == "approved":
        return (
            f"@{sender} 任务[{matched_task['title']}] 已完成!\n"
            f"审核: 通过 | 质量: {quality}\n"
            f"{reason}"
        )
    elif decision == "need_more":
        return (
            f"@{sender} 完成信息不足，请补充~\n"
            f"任务: {matched_task['title']}\n"
            f"{reason}"
        )
    else:
        return f"@{sender} 提交未通过: {reason}"


# ── 抽查处理 ──

def do_spot_check(member_name: str, member_id: int) -> str:
    """对指定成员发起抽查"""
    questions = [
        "请说明今天的学习内容和完成进度",
        "今天完成了哪些学习任务？有什么困难吗？",
        "请总结一下你最近三天的学习情况",
    ]
    import random
    question = random.choice(questions)

    create_spot_check(member_id, question)
    return f" 随机抽查：@{member_name}，{question}"


def handle_spot_check_reply(sender: str, content: str) -> str:
    """处理抽查回复"""
    db = __import__('database').get_db()
    mid = ensure_member(sender)
    # 找最近未回答的抽查
    row = db.execute(
        "SELECT * FROM spot_checks WHERE member_id = ? AND answer IS NULL "
        "ORDER BY created_at DESC LIMIT 1",
        (mid,)
    ).fetchone()
    db.close()

    if not row:
        return ""

    check = dict(row)
    ai_result = evaluate_spot_check(check["question"], content)
    answer_spot_check(check["id"], content, ai_result.get("comment", ""))

    status = ai_result.get("status", "normal")
    emoji = {"good": " ", "normal": " ", "warning": " "}.get(status, " ")

    return (
        f" @{sender} {emoji} 抽查记录成功\n"
        f" 状态：{status}\n"
        f" {ai_result.get('comment', '')}"
    )


# ── 提醒生成 ──

def generate_reminders() -> list:
    """生成所有到期提醒消息，返回 [(task_id, member_id, message), ...]"""
    tasks = get_pending_tasks()
    reminders = []

    for task in tasks:
        if not task.get("deadline"):
            continue

        try:
            deadline = datetime.fromisoformat(task["deadline"])
        except (ValueError, TypeError):
            continue

        now = datetime.now()
        hours_left = (deadline - now).total_seconds() / 3600

        if hours_left <= 0:
            # 已逾期
            update_task_status(task["id"], "已逾期")
            reminders.append((
                task["id"],
                task.get("publisher_id"),
                f" 「{task['title']}」已逾期！请说明原因。"
            ))
        elif hours_left <= 24:
            # 即将截止
            reminders.append((
                task["id"],
                task.get("publisher_id"),
                f" 「{task['title']}」将在 {deadline.strftime('%H:%M')} 截止，请及时完成！"
            ))

    return reminders


# ── 统计汇报 ──

def generate_stats_report() -> str:
    """生成学习统计报告"""
    stats = get_all_stats()
    if not stats:
        return "暂无成员数据。"

    lines = [" 本周学习情况：\n"]
    for s in stats:
        name = s.get("name", "?")
        completed = s.get("completed", 0)
        total = s.get("total", 0)
        overdue = s.get("overdue", 0)
        pct = f"{completed}/{total}" if total > 0 else "--"
        line = f"\n{name}：完成 {pct}"
        if overdue > 0:
            line += f"  逾期 {overdue} 次"
        lines.append(line)

    lines.append(f"\n---\n共 {len(stats)} 位成员")
    return "".join(lines)


# ── 辅助 ──

def _handle_general_chat(sender: str, content: str) -> str:
    """处理普通聊天消息（非任务/非完成）"""
    from ai import _call_deepseek
    prompt = (
        "你是一个微信群里的学习监督机器人，名字叫小督。用简短自然的口语回复群友。\n"
        "你可以：记录任务、检查完成情况、回答问题。\n"
        f"群友 {sender} 说：{content}\n"
        "请用一句话回复（20字以内），语气友好但不啰嗦。"
    )
    # API不可用时返回空（不回复）
    if not __import__('config').DEEPSEEK_API_KEY:
        return ""
    reply = _call_deepseek("你是微信群学习监督机器人小督，回复简短友好。", prompt, temperature=0.7)
    # 如果回退匹配返回了非JSON，说明API失败
    if reply and reply.startswith("{"):
        return ""  # 回退匹配的JSON，不该回复
    return reply.strip() if reply else ""


def _looks_like_completion(content: str) -> bool:
    """判断消息是否像完成汇报"""
    keywords = ["完成", "做完", "好了", "ok", "done", "搞定", "提交"]
    return any(kw in content.lower() for kw in keywords)


# ── 初始化 ──
if __name__ == "__main__":
    init_db()
    print("任务管理器就绪")

    # 快速测试
    print("\n=== 测试：任务发布 ===")
    reply = process_message("老师", "今天完成Python第三章练习，晚上8点截止，张三和李四负责")
    print(reply)

    print("\n=== 测试：任务完成(信息不足) ===")
    reply = process_message("张三", "完成了")
    print(reply)

    print("\n=== 统计 ===")
    print(generate_stats_report())
