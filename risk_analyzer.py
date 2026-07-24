# -*- coding: utf-8 -*-
"""
风险分析器 —— 综合评估成员学习风险
算法: 逾期率×40 + (100-完成率)×30 + 评分下降×20 + 连续未完成×10
完全由 Python 计算，不调用 AI
"""

from datetime import datetime, timedelta
from database import (
    get_db, list_members, get_latest_score, get_overdue_count,
    get_streak_fails, save_risk_assessment, get_latest_risk, get_all_risks,
)

RISK_LOW = "low"
RISK_MEDIUM = "medium"
RISK_HIGH = "high"

# ── 风险级别阈值 ──
RISK_THRESHOLD_MEDIUM = 30
RISK_THRESHOLD_HIGH = 60


def assess_member(member_id: int, member_name: str = "") -> dict:
    """
    评估单个成员的风险等级。
    返回:
      { "risk_level": "low/medium/high", "risk_score": 45.0,
        "completion_rate": 90, "overdue_count": 1,
        "score_trend": "stable", "streak_fails": 0, "detail": "..."
      }
    """
    db = get_db()

    # ── 1. 完成率 (100 - rate) ──
    total = db.execute(
        "SELECT COUNT(*) as c FROM task_assignees WHERE member_id = ?", (member_id,)
    ).fetchone()["c"]
    completed = db.execute(
        "SELECT COUNT(*) as c FROM task_assignees "
        "WHERE member_id = ? AND status = 'approved'", (member_id,)
    ).fetchone()["c"]
    completion_rate = (completed / total * 100) if total > 0 else 0.0

    # ── 2. 逾期次数 ──
    overdue_count = get_overdue_count(member_id)

    # ── 3. 评分趋势 (比较最近两次) ──
    score_trend = _calc_score_trend(db, member_id)

    # ── 4. 连续未完成 ──
    streak_fails = get_streak_fails(member_id)

    # ── 5. 最近一次抽查结果 ──
    last_check = db.execute(
        "SELECT ai_judgment FROM spot_checks WHERE member_id = ? "
        "ORDER BY created_at DESC LIMIT 1", (member_id,)
    ).fetchone()
    check_warning = False
    if last_check and last_check["ai_judgment"]:
        check_warning = "warning" in str(last_check["ai_judgment"]).lower()

    db.close()

    # ── 计算风险分 ──
    # 逾期率: 每逾期一次 +15, 上限 40
    overdue_score = min(overdue_count * 15, 40)

    # 完成率: (100 - rate) * 0.3
    completion_score = (100 - completion_rate) * 0.3

    # 评分趋势: down→20, stable→10, up→0
    trend_score = {"down": 20, "stable": 10, "up": 0}.get(score_trend, 10)

    # 连续未完成: 每次 +5, 上限 10
    fail_score = min(streak_fails * 5, 10)

    # 抽查警告: +5
    check_score = 5 if check_warning else 0

    risk_score = overdue_score + completion_score + trend_score + fail_score + check_score

    # ── 风险等级 ──
    if risk_score >= RISK_THRESHOLD_HIGH:
        risk_level = RISK_HIGH
    elif risk_score >= RISK_THRESHOLD_MEDIUM:
        risk_level = RISK_MEDIUM
    else:
        risk_level = RISK_LOW

    # ── 详细说明 ──
    detail_parts = []
    if overdue_count > 0:
        detail_parts.append(f"逾期{overdue_count}次")
    if completion_rate < 50:
        detail_parts.append(f"完成率仅{completion_rate:.0f}%")
    if score_trend == "down":
        detail_parts.append("评分下降趋势")
    if streak_fails >= 3:
        detail_parts.append(f"连续{streak_fails}次未完成")
    if check_warning:
        detail_parts.append("最近抽查异常")

    result = {
        "risk_level": risk_level,
        "risk_score": round(risk_score, 1),
        "completion_rate": round(completion_rate, 1),
        "overdue_count": overdue_count,
        "score_trend": score_trend,
        "streak_fails": streak_fails,
        "detail": "；".join(detail_parts) if detail_parts else "学习状态正常",
    }

    # ── 保存 ──
    import json
    save_risk_assessment(
        member_id, risk_level, risk_score,
        completion_rate, overdue_count,
        score_trend, streak_fails,
        json.dumps(result, ensure_ascii=False),
    )

    return {**result, "member_name": member_name}


def assess_all() -> list:
    """评估所有成员"""
    members = list_members()
    results = []
    for m in members:
        r = assess_member(m["id"], m.get("wx_name", ""))
        results.append(r)
    return results


def get_reminder_strategy(risk_level: str) -> dict:
    """
    根据风险等级返回提醒策略。
    { "frequency_multiplier": 1/2/3, "spot_check": True/False, "warning": True/False }
    """
    strategies = {
        RISK_LOW: {"frequency_multiplier": 1, "spot_check": False, "warning": False},
        RISK_MEDIUM: {"frequency_multiplier": 2, "spot_check": True, "warning": False},
        RISK_HIGH: {"frequency_multiplier": 3, "spot_check": True, "warning": True},
    }
    return strategies.get(risk_level, strategies[RISK_LOW])


# ── 辅助 ──

def _calc_score_trend(db, member_id: int) -> str:
    """比较最近两次评分判断趋势"""
    rows = db.execute(
        "SELECT overall_score FROM study_scores WHERE member_id = ? "
        "ORDER BY calculated_at DESC LIMIT 2", (member_id,)
    ).fetchall()
    if len(rows) < 2:
        return "stable"
    latest, previous = rows[0]["overall_score"], rows[1]["overall_score"]
    diff = latest - previous
    if diff > 5:
        return "up"
    elif diff < -5:
        return "down"
    return "stable"


# ── 测试 ──
if __name__ == "__main__":
    from database import init_db, ensure_member
    init_db()

    for name in ["张三", "李四"]:
        ensure_member(name)

    print("=== 风险评估 ===\n")
    results = assess_all()
    for r in results:
        level_emoji = {"low": "[LOW]", "medium": "[MED]", "high": "[HIGH]"}.get(r["risk_level"], "")
        print(f"{level_emoji} {r.get('member_name', '?')} 风险分: {r['risk_score']} | {r['detail']}")
        strategy = get_reminder_strategy(r["risk_level"])
        print(f"  策略: 提醒频率×{strategy['frequency_multiplier']} 抽查={strategy['spot_check']}")
        print()
