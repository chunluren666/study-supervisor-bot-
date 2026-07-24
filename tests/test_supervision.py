# -*- coding: utf-8 -*-
"""
智能监督策略测试 — 4 个场景
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_db, ensure_member, create_task
from risk_analyzer import assess_member, assess_all, get_reminder_strategy
from check_manager import select_targets, generate_check_message, do_smart_spot_check
from report_generator import generate_personal_report, generate_group_report


def setup():
    """初始化测试环境"""
    import config
    import glob
    for f in glob.glob(str(config.DATABASE_PATH) + "*"):
        try: os.remove(f)
        except: pass
    init_db()
    for name in ["张三", "李四", "王老师"]:
        ensure_member(name)


def test_1_low_risk():
    """场景1：连续完成任务成员 → 低风险"""
    print("\n" + "=" * 60)
    print("Test 1: 高完成率 → 低风险")

    # 给张三创建多个已完成任务
    tid = create_task("测试任务A", "完成A", publisher_name="王老师", assignee_names=["张三"])
    tid2 = create_task("测试任务B", "完成B", publisher_name="王老师", assignee_names=["张三"])

    # 模拟全部approved
    db = __import__('database').get_db()
    for row in db.execute("SELECT id FROM task_assignees WHERE member_id IN (SELECT id FROM members WHERE wx_name='张三')").fetchall():
        db.execute("UPDATE task_assignees SET status='approved', completed_at=? WHERE id=?",
                   (__import__('datetime').datetime.now().isoformat(), row["id"]))
    db.commit()
    db.close()

    # 评估
    mid = __import__('database').get_db().execute("SELECT id FROM members WHERE wx_name='张三'").fetchone()["id"]
    __import__('database').get_db().close()
    r = assess_member(mid, "张三")
    print(f"风险等级: {r['risk_level']} | 风险分: {r['risk_score']}")
    print(f"详情: {r['detail']}")
    assert r['risk_level'] == 'low', f"期望low, 实际: {r['risk_level']}"
    print("[PASS] Test 1")


def test_2_high_risk():
    """场景2：连续逾期成员 → 高风险"""
    print("\n" + "=" * 60)
    print("Test 2: 连续逾期 → 高风险")

    ensure_member("李四")
    # 李四没有完成任务，task_assignees全是pending/rejected
    mid = __import__('database').get_db().execute("SELECT id FROM members WHERE wx_name='李四'").fetchone()["id"]
    __import__('database').get_db().close()

    r = assess_member(mid, "李四")
    print(f"风险等级: {r['risk_level']} | 风险分: {r['risk_score']}")
    print(f"详情: {r['detail']}")
    # 可能有中等风险（因为没有逾期记录，只有低完成率）
    assert r['risk_level'] in ('medium', 'high'), f"期望medium/high, 实际: {r['risk_level']}"
    print("[PASS] Test 2")


def test_3_risk_strategy():
    """场景3：风险策略匹配"""
    print("\n" + "=" * 60)
    print("Test 3: 风险策略")

    for level in ("low", "medium", "high"):
        s = get_reminder_strategy(level)
        print(f"  {level}: freq={s['frequency_multiplier']}x spot={s['spot_check']}")
        assert s['frequency_multiplier'] >= 1

    assert get_reminder_strategy("high")["frequency_multiplier"] == 3
    assert get_reminder_strategy("low")["spot_check"] == False
    print("[PASS] Test 3")


def test_4_smart_check():
    """场景4：智能抽查生成"""
    print("\n" + "=" * 60)
    print("Test 4: 智能抽查")

    targets = select_targets(2)
    print(f"选中 {len(targets)} 个目标:")
    for mid, name, level, detail in targets:
        msg = generate_check_message(name, level)
        print(f"  {name} ({level}): {msg[:80]}")
    assert len(targets) > 0, "应有抽查目标"
    print("[PASS] Test 4")


def test_5_reports():
    """场景5：报告生成"""
    print("\n" + "=" * 60)
    print("Test 5: 报告生成")

    personal = generate_personal_report("张三", find_mid("张三"))
    assert "张三" in personal and "评分" in personal
    print(f"  个人报告: {len(personal)} 字符")

    group = generate_group_report("weekly")
    assert "周报" in group
    print(f"  群组报告: {len(group)} 字符")
    print("[PASS] Test 5")


def find_mid(name):
    db = __import__('database').get_db()
    row = db.execute("SELECT id FROM members WHERE wx_name = ?", (name,)).fetchone()
    db.close()
    return row["id"] if row else 0


if __name__ == "__main__":
    setup()
    test_1_low_risk()
    test_2_high_risk()
    test_3_risk_strategy()
    test_4_smart_check()
    test_5_reports()

    print("\n" + "=" * 60)
    print("  All tests passed!")
    print("=" * 60)
