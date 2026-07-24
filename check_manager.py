# -*- coding: utf-8 -*-
"""
智能抽查管理器 —— 根据风险等级和活跃度选择抽查对象
高风险优先 + 长时间未提交 + 评分下降 + 随机
"""

import random
from datetime import datetime, timedelta
from database import get_db, list_members, create_spot_check, get_latest_risk
from risk_analyzer import RISK_HIGH, RISK_MEDIUM, RISK_LOW, assess_all


# ── 抽查问题模板 ──
CHECK_QUESTIONS = {
    RISK_HIGH: [
        "请说明最近3个任务的完成情况，如有逾期请说明原因",
        "你的学习进度明显落后，请具体说明当前状态和遇到的困难",
        "连续多次未按时完成，请制定补救计划并说明时间安排",
    ],
    RISK_MEDIUM: [
        "请汇报今日学习内容和完成进度",
        "请说明当前任务的完成情况，有什么需要帮助的？",
        "最近完成率有所下降，请说明原因",
    ],
    RISK_LOW: [
        "请简短汇报今天的学习内容",
        "今天完成了哪些学习任务？",
        "请用一句话总结今天的学习收获",
    ],
}


def select_targets(count: int = 2) -> list:
    """
    智能选择抽查目标。
    优先级: 高风险 > 上次抽查距今 > 评分下降 > 随机
    返回: [(member_id, wx_name, risk_level, reason), ...]
    """
    risks = assess_all()
    if not risks:
        return []

    db = get_db()

    # 按优先级排序
    scored = []
    for r in risks:
        score = 0
        # 风险等级权重
        score += {"high": 100, "medium": 50, "low": 10}.get(r["risk_level"], 0)
        # 逾期次数
        score += r["overdue_count"] * 15
        # 连续未完成
        score += r["streak_fails"] * 10
        # 长时间未抽查（>3天加分）
        last_check = db.execute(
            "SELECT created_at FROM spot_checks WHERE member_id = ? "
            "ORDER BY created_at DESC LIMIT 1",
            (find_member_id(r.get("member_name", "")),)
        ).fetchone()
        if last_check:
            try:
                days_since = (datetime.now() - datetime.fromisoformat(
                    last_check["created_at"])).days
                if days_since > 3:
                    score += days_since * 5
            except (ValueError, TypeError):
                score += 20  # 无法解析，加基础分
        else:
            score += 20  # 从未被抽查
        scored.append((r, score))

    db.close()

    # 排序取 top N
    scored.sort(key=lambda x: x[1], reverse=True)
    targets = []
    for r, score in scored[:count]:
        mid = find_member_id(r.get("member_name", ""))
        if mid:
            targets.append((mid, r.get("member_name", ""), r["risk_level"], r["detail"]))
    return targets


def generate_check_message(member_name: str, risk_level: str) -> str:
    """根据风险等级生成个性化抽查消息"""
    questions = CHECK_QUESTIONS.get(risk_level, CHECK_QUESTIONS[RISK_LOW])
    question = random.choice(questions)
    return f" 随机抽查：@{member_name}，{question}"


def do_smart_spot_check(count: int = 2) -> list:
    """
    执行智能抽查，返回发送消息列表。
    """
    targets = select_targets(count)
    messages = []
    for mid, name, risk_level, detail in targets:
        msg = generate_check_message(name, risk_level)
        create_spot_check(mid, msg)
        messages.append(msg)
    return messages


def find_member_id(name: str) -> int:
    """根据名字找 member_id"""
    db = get_db()
    row = db.execute("SELECT id FROM members WHERE wx_name = ?", (name,)).fetchone()
    db.close()
    return row["id"] if row else 0


# ── 测试 ──
if __name__ == "__main__":
    from database import init_db, ensure_member
    init_db()
    for name in ["张三", "李四", "王老师"]:
        ensure_member(name)

    print("=== 智能抽查测试 ===\n")
    targets = select_targets(3)
    for mid, name, level, detail in targets:
        print(f"目标: {name} (风险: {level}) - {detail}")
        msg = generate_check_message(name, level)
        print(f"  消息: {msg[:80]}\n")
