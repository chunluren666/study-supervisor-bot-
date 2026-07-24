# -*- coding: utf-8 -*-
"""
学习评分系统
权重固定: 完成率40% + 及时率30% + 质量30%
Python 计算，AI 只负责质量文字评价
"""

import json
from datetime import datetime, timedelta
from database import (
    get_db, list_members, get_latest_score, save_score,
)


# ── 评分权重（固定） ──
WEIGHT_COMPLETION = 0.40   # 完成率
WEIGHT_TIMELINESS = 0.30   # 及时率
WEIGHT_QUALITY = 0.30      # 质量评分


def calculate_member_score(member_id: int, member_name: str = "") -> dict:
    """
    计算单个成员的学习评分。
    返回:
      {
        "member_name": "张三",
        "completion_rate": 85.0,    # 完成率 0-100
        "timeliness_rate": 90.0,    # 及时率 0-100
        "quality_score": 80.0,      # 质量 0-100
        "overall_score": 84.5,      # 综合评分
        "streak_days": 7,           # 连续学习天数
        "comment": "学习状态良好",
      }
    """
    db = get_db()

    # ── 1. 完成率 = 已完成任务数 / 总任务数 × 100 ──
    total = db.execute(
        "SELECT COUNT(*) as c FROM task_assignees WHERE member_id = ?",
        (member_id,)
    ).fetchone()["c"]
    completed = db.execute(
        "SELECT COUNT(*) as c FROM task_assignees "
        "WHERE member_id = ? AND status = 'approved'",
        (member_id,)
    ).fetchone()["c"]
    completion_rate = (completed / total * 100) if total > 0 else 0.0

    # ── 2. 及时率 = 截止时间前完成的任务数 / 已完成任务数 × 100 ──
    on_time = 0
    if completed > 0:
        rows = db.execute(
            "SELECT ta.completed_at, t.deadline "
            "FROM task_assignees ta JOIN tasks t ON ta.task_id = t.id "
            "WHERE ta.member_id = ? AND ta.status = 'approved'",
            (member_id,)
        ).fetchall()
        for r in rows:
            if r["completed_at"] and r["deadline"]:
                try:
                    completed_dt = datetime.fromisoformat(r["completed_at"])
                    deadline_dt = datetime.fromisoformat(r["deadline"])
                    if completed_dt <= deadline_dt:
                        on_time += 1
                except (ValueError, TypeError):
                    on_time += 1  # 无法解析则算及时
            else:
                on_time += 1
    timeliness_rate = (on_time / completed * 100) if completed > 0 else 0.0

    # ── 3. 质量 = AI审核通过率中"good"所占比例 ──
    quality_count = db.execute(
        "SELECT COUNT(*) as c FROM completion_evidence ce "
        "JOIN task_assignees ta ON ce.assignee_id = ta.id "
        "WHERE ta.member_id = ? AND ce.ai_audit_result = 'approved'",
        (member_id,)
    ).fetchone()["c"]
    # 质量基于evidence的audit结果
    good_count = db.execute(
        "SELECT COUNT(*) as c FROM completion_evidence ce "
        "JOIN task_assignees ta ON ce.assignee_id = ta.id "
        "WHERE ta.member_id = ? AND ce.ai_audit_result = 'approved' ",
        (member_id,)
    ).fetchone()["c"]
    quality_score = 70.0  # 默认基础分

    # 如果有已审核的证据，从AI评价中提取质量信息
    evidence_rows = db.execute(
        "SELECT ce.ai_audit_reason, ce.ai_audit_result "
        "FROM completion_evidence ce "
        "JOIN task_assignees ta ON ce.assignee_id = ta.id "
        "WHERE ta.member_id = ? AND ce.ai_audit_reason IS NOT NULL "
        "ORDER BY ce.submitted_at DESC LIMIT 10",
        (member_id,)
    ).fetchall()

    if evidence_rows:
        # 简单统计: passed且reason包含正面词 → 高分
        passed = sum(1 for r in evidence_rows if r["ai_audit_result"] == "approved")
        quality_score = (passed / len(evidence_rows) * 100) if evidence_rows else 70.0

    # ── 4. 连续学习天数 ──
    streak_days = _calculate_streak(db, member_id)

    # ── 5. 综合评分 ──
    overall = (
        completion_rate * WEIGHT_COMPLETION +
        timeliness_rate * WEIGHT_TIMELINESS +
        quality_score * WEIGHT_QUALITY
    )

    # ── 6. 评价文字 ──
    comment = _generate_comment(overall, completion_rate, timeliness_rate, streak_days)

    db.close()

    result = {
        "member_name": member_name,
        "completion_rate": round(completion_rate, 1),
        "timeliness_rate": round(timeliness_rate, 1),
        "quality_score": round(quality_score, 1),
        "overall_score": round(overall, 1),
        "streak_days": streak_days,
        "comment": comment,
    }

    # 保存到数据库
    save_score(
        member_id,
        completion_rate=result["completion_rate"],
        timeliness_rate=result["timeliness_rate"],
        quality_score=result["quality_score"],
        overall_score=result["overall_score"],
        streak_days=streak_days,
        comment=comment,
    )

    return result


def calculate_all_scores() -> list:
    """计算所有成员的评分"""
    members = list_members()
    results = []
    for m in members:
        score = calculate_member_score(m["id"], m.get("wx_name", ""))
        results.append(score)
    return results


def get_leaderboard() -> list:
    """获取排行榜，按综合评分降序"""
    scores = calculate_all_scores()
    scores.sort(key=lambda x: x["overall_score"], reverse=True)
    return scores


# ── 辅助 ──

def _calculate_streak(db, member_id: int) -> int:
    """计算连续学习天数"""
    rows = db.execute(
        "SELECT DISTINCT DATE(completed_at) as d FROM task_assignees "
        "WHERE member_id = ? AND status = 'approved' AND completed_at IS NOT NULL "
        "ORDER BY d DESC LIMIT 30",
        (member_id,)
    ).fetchall()

    if not rows:
        return 0

    dates = []
    for r in rows:
        try:
            dates.append(datetime.fromisoformat(r["d"]).date())
        except (ValueError, TypeError):
            continue

    if not dates:
        return 0

    # 计算从今天往前的连续天数
    today = datetime.now().date()
    streak = 0
    check_date = today
    for d in sorted(dates, reverse=True):
        if d == check_date or d == check_date - timedelta(days=1):
            streak += 1
            check_date = d
        elif d < check_date - timedelta(days=1):
            break
    return streak


def _generate_comment(overall: float, completion: float, timeliness: float,
                      streak: int) -> str:
    """根据分数生成文字评价"""
    if overall >= 90:
        base = "学习状态优秀"
    elif overall >= 75:
        base = "学习状态良好"
    elif overall >= 60:
        base = "学习状态一般，需要努力"
    else:
        base = "学习状态较差，需要改进"

    parts = [base]
    if completion < 50:
        parts.append("完成率偏低")
    if timeliness < 50:
        parts.append("需要提高及时性")
    if streak >= 7:
        parts.append(f"已连续学习 {streak} 天")

    return "，".join(parts)


# ── 测试 ──
if __name__ == "__main__":
    from database import init_db, ensure_member
    init_db()

    # 创建测试成员
    for name in ["张三", "李四"]:
        ensure_member(name)

    print("=== 学习评分 ===\n")
    scores = calculate_all_scores()
    for s in scores:
        print(f"{s['member_name']}: 综合 {s['overall_score']} 分")
        print(f"  完成率: {s['completion_rate']}% | 及时率: {s['timeliness_rate']}% | 质量: {s['quality_score']}%")
        print(f"  连续学习: {s['streak_days']} 天")
        print(f"  评价: {s['comment']}")
        print()

    print("=== 排行榜 ===")
    for i, s in enumerate(get_leaderboard(), 1):
        print(f"{i}. {s['member_name']} - {s['overall_score']} 分")
