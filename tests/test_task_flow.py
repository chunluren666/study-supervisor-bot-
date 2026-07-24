# -*- coding: utf-8 -*-
"""
任务流程测试 — 模拟 3 个完成场景
运行: python -m tests.test_task_flow
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import (
    init_db, ensure_member, create_task, get_tasks_by_member,
    get_assignee_by_task_and_member, get_evidence, get_latest_score,
    STATUS_APPROVED, STATUS_REJECTED,
)
from task_manager import process_message, generate_stats_report
from study_score import calculate_all_scores


def setup_test_data():
    """初始化测试数据"""
    # 清空旧数据库
    import config
    db_path = config.DATABASE_PATH
    for ext in ['', '-wal', '-shm']:
        try: os.remove(str(db_path) + ext)
        except: pass

    init_db()

    # 创建成员
    for name in ["张三", "李四", "王老师"]:
        ensure_member(name)

    # 创建任务
    task_id = create_task(
        title="高等数理统计第三章学习",
        content="完成高等数理统计第三章全部学习内容，并完成全部课后习题。截止本周五前提交。",
        deadline="2026-07-25T23:59:00",
        publisher_name="王老师",
        assignee_names=["张三", "李四"],
    )

    print(f"测试数据就绪: 任务ID={task_id}, 成员: 张三, 李四")
    return task_id


def test_scenario_A():
    """场景A: 信息不足 — "我完成了" """
    print("\n" + "=" * 60)
    print("场景A: 学生仅说「我完成了」")
    print("=" * 60)

    reply = process_message("张三", "我完成了")
    print(f"回复: {reply}")

    # 验证
    tasks = get_tasks_by_member("张三")
    status = tasks[0]["assignee_status"] if tasks else "?"

    print(f"任务状态: {status}")
    assert "补充" in reply or "信息不足" in reply or "need_more" in reply.lower(), \
        "AI应要求补充信息"
    print("[PASS] 场景A 通过")


def test_scenario_B():
    """场景B: 部分完成 — "第三章已经看完，习题完成50%" """
    print("\n" + "=" * 60)
    print("场景B: 学生说「第三章看了，习题做了50%」")
    print("=" * 60)

    reply = process_message("李四", "第三章已经看完，习题完成50%")
    print(f"回复: {reply}")

    tasks = get_tasks_by_member("李四")
    status = tasks[0]["assignee_status"] if tasks else "?"

    print(f"任务状态: {status}")
    # 应该是 rejected，因为未完成
    assert status in (STATUS_REJECTED, "submitted"), \
        f"部分完成应被拒绝或待补充，当前状态: {status}"
    print("[PASS] 场景B 通过")


def test_scenario_C():
    """场景C: 完整提交 — 全部完成 + 证据"""
    print("\n" + "=" * 60)
    print("场景C: 学生提交完整证据")
    print("=" * 60)

    reply = process_message(
        "张三",
        "高等数理统计第三章学习完成。全部15道课后习题已完成，笔记整理了3页A4纸，"
        "包括参数估计、假设检验、方差分析三部分的知识点总结。"
    )
    print(f"回复: {reply}")

    tasks = get_tasks_by_member("张三")
    status = tasks[0]["assignee_status"] if tasks else "?"

    print(f"任务状态: {status}")
    assert status == STATUS_APPROVED, \
        f"完整提交应被批准，当前状态: {status}"
    print("[PASS] 场景C 通过")


def test_scoring():
    """测试评分系统"""
    print("\n" + "=" * 60)
    print("评分系统测试")
    print("=" * 60)

    scores = calculate_all_scores()
    for s in scores:
        print(f"\n{s['member_name']}:")
        print(f"  综合: {s['overall_score']} 分")
        print(f"  完成率: {s['completion_rate']}%")
        print(f"  及时率: {s['timeliness_rate']}%")
        print(f"  质量: {s['quality_score']}%")
        print(f"  连续: {s['streak_days']} 天")
        print(f"  评价: {s['comment']}")

    assert len(scores) > 0, "应有评分数据"
    # 张三完成1/1任务，应该有较高分
    zhangsan = next((s for s in scores if s['member_name'] == '张三'), None)
    if zhangsan:
        assert zhangsan['completion_rate'] > 0, "张三应有完成率"
    print("\n[PASS] 评分测试通过")


def test_stats():
    """测试统计报告"""
    print("\n" + "=" * 60)
    print("统计报告")
    print("=" * 60)
    report = generate_stats_report()
    print(report)
    assert "张三" in report, "统计应包含张三"
    assert "李四" in report, "统计应包含李四"
    print("[PASS] 统计测试通过")


if __name__ == "__main__":
    print("=" * 60)
    print("  任务流程测试套件")
    print("=" * 60)

    setup_test_data()

    test_scenario_A()
    test_scenario_B()
    test_scenario_C()
    test_scoring()
    test_stats()

    print("\n" + "=" * 60)
    print("  全部测试通过 [PASS]")
    print("=" * 60)
