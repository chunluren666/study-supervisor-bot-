# -*- coding: utf-8 -*-
"""
报告生成器 —— 个人报告 / 群报告 / 周报 / 月报
"""

from datetime import datetime, timedelta
from database import (
    get_db, list_members, get_latest_score, get_all_risks,
    save_report, get_reports,
)
from risk_analyzer import assess_all


def generate_personal_report(member_name: str, member_id: int) -> str:
    """生成个人学习报告"""
    db = get_db()
    score = get_latest_score(member_id)
    risk = get_all_risks()
    risk_info = next((r for r in risk if r.get("wx_name") == member_name), {})

    # 近期完成记录
    recent = db.execute(
        "SELECT ta.status, ta.completed_at, t.title FROM task_assignees ta "
        "JOIN tasks t ON ta.task_id = t.id "
        "WHERE ta.member_id = ? ORDER BY ta.id DESC LIMIT 5",
        (member_id,)
    ).fetchall()
    db.close()

    lines = [f" {member_name} 学习报告", "=" * 30, ""]

    # 评分
    if score:
        lines.append(f"综合评分: {score.get('overall_score', 0)} 分")
        lines.append(f"完成率: {score.get('completion_rate', 0)}%")
        lines.append(f"及时率: {score.get('timeliness_rate', 0)}%")
        lines.append(f"连续学习: {score.get('streak_days', 0)} 天")
        lines.append(f"评价: {score.get('comment', '暂无')}")
    else:
        lines.append("暂无评分数据")

    # 风险
    if risk_info:
        level_str = {"low": "低风险", "medium": "中风险", "high": "高风险"}.get(
            risk_info.get("risk_level", "low"), "低风险")
        lines.append(f"风险等级: {level_str}")

    # 最近任务
    lines.append(f"\n 最近任务:")
    for r in recent:
        status_str = {"approved": "[OK]", "rejected": "[X]", "submitted": "[...]", "pending": "[ ]"}.get(
            r["status"], "[ ]")
        lines.append(f"  {status_str} {r['title']}")

    return "\n".join(lines)


def generate_group_report(report_type: str = "weekly") -> str:
    """生成群组报告"""
    now = datetime.now()

    if report_type == "weekly":
        title = f"周报 ({now.strftime('%m/%d')} - {(now - timedelta(days=7)).strftime('%m/%d')})"
    else:
        title = f"月报 ({now.strftime('%Y年%m月')})"

    risks = assess_all()
    scores = [get_latest_score(find_member_id(r.get("member_name", "")))
              for r in risks]

    lines = [f" {title}", "=" * 30, ""]

    # 整体统计
    all_scores = [s.get("overall_score", 0) for s in scores if s]
    avg_score = sum(all_scores) / len(all_scores) if all_scores else 0

    high_risk = [r for r in risks if r["risk_level"] == "high"]
    low_risk = [r for r in risks if r["risk_level"] == "low"]

    lines.append(f"整体完成率: {avg_score:.0f} 分")
    lines.append(f"高风险成员: {len(high_risk)} 人")
    lines.append(f"低风险成员: {len(low_risk)} 人")

    # 优秀成员 (评分 > 80)
    excellent = [r for r in risks if r.get("completion_rate", 0) > 80]
    if excellent:
        lines.append(f"\n 优秀成员: {', '.join(r.get('member_name', '?') for r in excellent)}")

    # 需关注成员
    if high_risk:
        lines.append(f"\n 需关注:")
        for r in high_risk:
            lines.append(f"  {r.get('member_name', '?')} - {r.get('detail', '')}")

    # 趋势简要
    lines.append(f"\n---")
    lines.append(f"共 {len(risks)} 位成员")

    content = "\n".join(lines)

    # 保存
    save_report(report_type, title, content)

    return content


def find_member_id(name: str) -> int:
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

    print("=== 群组周报 ===\n")
    print(generate_group_report("weekly"))

    print("\n\n=== 张三个人报告 ===\n")
    print(generate_personal_report("张三", find_member_id("张三")))
