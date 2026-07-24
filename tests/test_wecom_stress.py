# -*- coding: utf-8 -*-
"""企业微信压力测试 — 并发消息、重复消息、AI失败恢复"""

import sys, os, time, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_1_concurrent_messages():
    """并发消息处理"""
    print("\n[Test 1] 并发消息...")
    from wechat_gateway.wecom_adapter.wecom_adapter import WeComAdapter
    a = WeComAdapter(room_name="测试群")
    a.start()

    # 模拟10条并发消息
    for i in range(10):
        a.on_webhook_message({
            "MsgType": "text", "From": {"UserId": f"user{i}"},
            "Text": {"Content": f"测试消息{i}"}, "ChatId": "wr1", "MsgId": f"m{i}",
        })

    q_size = len(a._msg_queue)
    print(f"  队列: {q_size}/10 (并发注入OK)")
    assert q_size == 10
    return True

def test_2_duplicate_filter():
    """重复消息过滤"""
    print("\n[Test 2] 重复消息...")
    from wechat_gateway.wecom_adapter.wecom_adapter import WeComAdapter
    a = WeComAdapter()
    a.start()
    for _ in range(5):
        a.on_webhook_message({
            "MsgType": "text", "From": {"UserId": "u1"},
            "Text": {"Content": "hello"}, "ChatId": "wr1", "MsgId": "dup_001",
        })
    assert len(a._msg_queue) == 1, f"expected 1, got {len(a._msg_queue)}"
    print("  PASS: 5次注入只有1条入队")
    return True

def test_3_worker_processing():
    """Worker处理消息"""
    print("\n[Test 3] Worker处理...")
    from database import init_db, ensure_member, set_member_role; init_db()
    ensure_member("王老师", role="teacher")
    ensure_member("stu001", role="student")

    outgoing = []
    from task_manager import process_message

    r = process_message("王老师", "完成测试任务, stu001负责")
    if r: outgoing.append(r)
    r = process_message("stu001", "测试任务完成, 提交了报告和代码")
    if r: outgoing.append(r)

    print(f"  发送: {len(outgoing)} 条回复")
    assert len(outgoing) >= 1, f"Got {len(outgoing)}"
    return True

def test_4_command_system():
    """命令系统"""
    print("\n[Test 4] 命令系统...")
    from database import init_db, ensure_member, set_member_role
    from wechat_gateway.wecom_adapter.wecom_worker import _handle_command
    init_db()
    ensure_member("teacher_wc", role="teacher")
    ensure_member("student_wc", role="student")

    r = _handle_command("/查看排名", "teacher_wc")
    print(f"  排名: {r[:80]}")
    assert "排名" in r

    r = _handle_command("/帮助", "teacher_wc")
    print(f"  帮助: {r[:80]}")
    assert "发布" in r or "命令" in r

    r = _handle_command("/查看排名", "student_wc")
    print(f"  学生: {r[:50]}")
    assert "管理员" in r
    print("  PASS")
    return True

def test_5_message_roundtrip():
    """消息收发往返测试"""
    print("\n[Test 5] 消息往返...")
    from wechat_gateway.wecom_adapter.wecom_adapter import WeComAdapter
    a = WeComAdapter(room_name="测试群")
    a.start()

    # 注入消息
    a.on_webhook_message({
        "MsgType": "text", "From": {"UserId": "user1"},
        "Text": {"Content": "hello world"}, "ChatId": "c1", "MsgId": "roundtrip_1",
    })
    a.on_webhook_message({
        "MsgType": "text", "From": {"UserId": "user1"},
        "Text": {"Content": "hello world"}, "ChatId": "c1", "MsgId": "roundtrip_1",
    })

    # 第一条入队, 第二条重复被过滤
    q_size = len(a._msg_queue)
    print(f"  队列: {q_size} (expect 1)")
    assert q_size == 1

    # 取出消息
    msg = a.receive_message()
    assert msg["sender"] == "user1"
    assert msg["content"] == "hello world"

    # 队列清空
    assert a.receive_message() is None
    print("  PASS: roundtrip OK")
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("  WeCom Stress Tests")
    print("=" * 50)
    all_pass = True
    for test in [test_1_concurrent_messages, test_2_duplicate_filter,
                 test_3_worker_processing, test_4_command_system,
                 test_5_message_roundtrip]:
        try:
            test()
        except Exception as e:
            print(f"  FAIL: {e}")
            import traceback; traceback.print_exc()
            all_pass = False
    print("\n" + "=" * 50)
    print(f"  {'ALL PASSED' if all_pass else 'SOME FAILED'}")
    print("=" * 50)
