# -*- coding: utf-8 -*-
"""对话学习 — 从每日聊天中提取模式, 持续优化回复"""

import json, re
from datetime import date, datetime
from pathlib import Path
from database import get_db

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
LEARNED_FILE = DATA_DIR / "learned_patterns.json"


def analyze_today_conversations() -> dict:
    """分析今日对话, 提取优化建议"""
    today = date.today().isoformat()
    db = get_db()
    rows = db.execute(
        "SELECT user_id, content, timestamp FROM wecom_message_log "
        "WHERE DATE(timestamp)=? ORDER BY timestamp", (today,)
    ).fetchall()
    db.close()

    if not rows:
        return {"status": "no_data"}

    # 统计
    users = {}
    patterns = {"plan_submit": 0, "vague_reply": 0, "detailed_reply": 0,
                "question_asked": 0, "daily_plan": 0}
    total_chars = 0

    for r in rows:
        uid = r["user_id"]
        content = r["content"] or ""
        total_chars += len(content)
        users[uid] = users.get(uid, 0) + 1

        if any(kw in content for kw in ["今天要", "今天做", "今日计划", "今天完成"]):
            patterns["daily_plan"] += 1
        elif len(content) < 5:
            patterns["vague_reply"] += 1
        elif len(content) > 50 and any(kw in content for kw in ["完成", "做了", "做完"]):
            patterns["detailed_reply"] += 1
        elif "?" in content or "什么" in content or "怎么" in content:
            patterns["question_asked"] += 1

    # 学习建议
    suggestions = []
    if patterns["vague_reply"] > patterns["detailed_reply"]:
        suggestions.append("学生倾向于敷衍回复, 需要更严格的追问")
    if patterns["daily_plan"] > 0:
        suggestions.append(f"今日收到 {patterns['daily_plan']} 次计划提交, 计划模板运行良好")
    if patterns["question_asked"] > 0:
        suggestions.append("学生有疑问, 考虑增加FAQ自动回复")
    if total_chars / max(len(rows), 1) < 20:
        suggestions.append("平均消息长度偏短, 鼓励学生多说细节")

    return {
        "total_messages": len(rows),
        "active_users": len(users),
        "patterns": patterns,
        "avg_chars": total_chars // max(len(rows), 1),
        "suggestions": suggestions,
        "analyzed_at": datetime.now().isoformat(),
    }


def get_learned_context(user_id: str) -> dict:
    """获取对学生历史对话中学习到的上下文"""
    db = get_db()
    # 最近3天的对话摘要
    rows = db.execute(
        "SELECT content, timestamp FROM wecom_message_log "
        "WHERE user_id=? ORDER BY timestamp DESC LIMIT 20", (user_id,)
    ).fetchall()
    db.close()

    subjects = set()
    counts = []
    for r in rows:
        content = r["content"] or ""
        # 提取学科
        for subj in ["数学", "英语", "政治", "专业课", "单词", "真题", "阅读", "习题",
                     "880", "660", "810", "1000", "1800"]:
            if subj in content:
                subjects.add(subj)
        # 提取数字(数量)
        nums = re.findall(r'(\d+)[道题个遍篇页]', content)
        counts.extend(nums)

    return {
        "mentioned_subjects": list(subjects),
        "recent_counts": counts[-5:],
        "total_recent_msgs": len(rows),
    }


def generate_daily_summary() -> str:
    """生成每日对话分析报告"""
    analysis = analyze_today_conversations()
    if analysis.get("status") == "no_data":
        return "今日无对话数据。"

    lines = [" 今日对话分析", ""]
    lines.append(f"消息总数: {analysis['total_messages']}")
    lines.append(f"活跃用户: {analysis['active_users']}")
    lines.append(f"平均长度: {analysis['avg_chars']}字")
    lines.append("")

    p = analysis["patterns"]
    lines.append(f"计划提交: {p['daily_plan']} | 敷衍回复: {p['vague_reply']} | 详细汇报: {p['detailed_reply']}")

    if analysis["suggestions"]:
        lines.append("\n优化建议:")
        for s in analysis["suggestions"]:
            lines.append(f"  - {s}")

    # 保存
    Path(LEARNED_FILE).write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
    return "\n".join(lines)
