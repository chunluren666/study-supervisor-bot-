#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demo Runner — 模拟完整学习监督场景
"""

import sys, os, time, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 清空旧数据
import config
for ext in ['', '-wal', '-shm']:
    try: os.remove(str(config.DATABASE_PATH) + ext)
    except: pass

from database import *
init_db()

print("=" * 60)
print("  学习监督机器人 — 产品演示")
print("=" * 60)

# ═══════════════════════════════════════
# 0. 角色设置
# ═══════════════════════════════════════
print("\n> 0. 角色设置")
ensure_member("王老师", role=ROLE_TEACHER)
ensure_member("小明", role=ROLE_STUDENT)
ensure_member("小红", role=ROLE_STUDENT)
ensure_member("小刚", role=ROLE_STUDENT)
print("   王老师(teacher) 小明(student) 小红(student) 小刚(student)")

# ═══════════════════════════════════════
# 1. 老师发布任务
# ═══════════════════════════════════════
print("\n" + "-" * 60)
print("> 1. 王老师发布任务")
print("-" * 60)

from task_manager import process_message

msg = "本周五前完成概率论第三章全部习题，并提交学习笔记。小明、小红、小刚负责。"
print(f"   王老师: \"{msg}\"")
time.sleep(0.3)

reply = process_message("王老师", msg)
print(f"   机器人: {reply[:200]}")
time.sleep(0.3)

# ═══════════════════════════════════════
# 2. 小明正常完成（提交详细证据）
# ═══════════════════════════════════════
print("\n" + "-" * 60)
print("> 2. 小明提交完整证据")
print("-" * 60)

msg = "概率论第三章已完成。全部12道习题做完，笔记整理了4页A4纸，包括条件概率、贝叶斯公式、随机变量三部分。"
print(f"   小明: \"{msg[:80]}...\"")
time.sleep(0.3)

reply = process_message("小明", msg)
print(f"   机器人: {reply[:200]}")
time.sleep(0.3)

# ═══════════════════════════════════════
# 3. 小红敷衍提交
# ═══════════════════════════════════════
print("\n" + "-" * 60)
print("> 3. 小红敷衍提交")
print("-" * 60)

msg = "做完了"
print(f"   小红: \"{msg}\"")
time.sleep(0.3)

reply = process_message("小红", msg)
print(f"   机器人: {reply[:200]}")
time.sleep(0.3)

# ═══════════════════════════════════════
# 4. 小刚完全没交（逾期）
# ═══════════════════════════════════════
print("\n" + "-" * 60)
print("> 4. 小刚逾期未提交")
print("-" * 60)
print("   小刚: (无任何回复)")
# 手动标记逾期
db = get_db()
row = db.execute(
    "SELECT ta.id FROM task_assignees ta JOIN members m ON ta.member_id=m.id "
    "WHERE m.wx_name='小刚' AND ta.status != 'approved'"
).fetchone()
if row:
    db.execute("UPDATE task_assignees SET status='rejected', ai_audit_reason='未提交任何内容，逾期' WHERE id=?",
               (row["id"],))
db.commit()
db.close()
print("   机器人: 小刚未提交任何内容，标记为逾期")

# ═══════════════════════════════════════
# 5. 学习评分
# ═══════════════════════════════════════
print("\n" + "-" * 60)
print("> 5. 学习评分")
print("-" * 60)

from study_score import calculate_all_scores
scores = calculate_all_scores()
for s in scores:
    bar = "█" * int(s["overall_score"] / 10) + "░" * (10 - int(s["overall_score"] / 10))
    print(f"   {s['member_name']:6s} | {bar} | {s['overall_score']:5.0f} 分 | 完成:{s['completion_rate']:.0f}% 及时:{s['timeliness_rate']:.0f}% 质量:{s['quality_score']:.0f}%")
    print(f"          {s['comment']}")
time.sleep(0.3)

# ═══════════════════════════════════════
# 6. 风险分析
# ═══════════════════════════════════════
print("\n" + "-" * 60)
print("> 6. 风险分析")
print("-" * 60)

from risk_analyzer import assess_all
risks = assess_all()
level_display = {"low": "低风险 🟢", "medium": "中风险 🟡", "high": "高风险 🔴"}
for r in risks:
    name = r.get("member_name", "?")
    print(f"   {name:6s} | {level_display.get(r['risk_level'], '?'):10s} | 风险分:{r['risk_score']:.0f} | {r['detail']}")
time.sleep(0.3)

# ═══════════════════════════════════════
# 7. 自动提醒
# ═══════════════════════════════════════
print("\n" + "-" * 60)
print("> 7. 自动提醒")
print("-" * 60)

from task_manager import generate_reminders
reminders = generate_reminders()
for tid, mid, msg in reminders:
    print(f"   [提醒] {msg[:100]}")
if not reminders:
    print("   (暂无到期提醒)")

# ═══════════════════════════════════════
# 8. 智能抽查
# ═══════════════════════════════════════
print("\n" + "-" * 60)
print("> 8. 智能抽查")
print("-" * 60)

from check_manager import do_smart_spot_check
checks = do_smart_spot_check(2)
for msg in checks:
    print(f"   {msg[:120]}")

# ═══════════════════════════════════════
# 9. 周报
# ═══════════════════════════════════════
print("\n" + "-" * 60)
print("> 9. 周报")
print("-" * 60)

from report_generator import generate_group_report, generate_personal_report
report = generate_group_report("weekly")
print(report)

# ═══════════════════════════════════════
# 10. 总结
# ═══════════════════════════════════════
print("\n" + "=" * 60)
print("  演示完成!")
print("=" * 60)
print(f"""
  场景总结:
  +--------+----------+----------+----------┐
  │ 成员   │ 行为     │ AI审核   │ 风险     │
  |--------┼----------┼----------┼----------┤
  │ 小明   │ 详细提交 │ 通过     │ 低       │
  │ 小红   │ 敷衍一句 │ 驳回     │ 中       │
  │ 小刚   │ 完全没交 │ 逾期标记 │ 高       │
  └--------┴----------┴----------┴----------┘

  完整流程: 任务发布 → AI审核 → 评分 → 风险 → 提醒 → 抽查 → 周报
""")
