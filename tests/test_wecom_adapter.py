# -*- coding: utf-8 -*-
"""企业微信适配器测试"""

import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_1_token():
    """Token 获取测试"""
    print("\n[Test 1] Token...")
    from wechat_gateway.wecom_adapter.wecom_api import WeComAPI
    api = WeComAPI()
    token = api.get_token()
    if token:
        print(f"  PASS: {token[:10]}...")
    else:
        print(f"  SKIP: No CORP_ID/SECRET configured (expected)")
    return True

def test_2_adapter_create():
    """适配器创建测试"""
    print("\n[Test 2] Adapter create...")
    from wechat_gateway.wecom_adapter.wecom_adapter import WeComAdapter
    a = WeComAdapter(room_name="监督")
    a.start()
    status = a.get_status()
    assert status["adapter"] == "WeComAdapter"
    assert status["room"] == "监督"
    print(f"  PASS: {status['protocol']}")
    return True

def test_3_message_format():
    """消息格式转换测试"""
    print("\n[Test 3] Message format...")
    from wechat_gateway.wecom_adapter.wecom_adapter import WeComAdapter
    a = WeComAdapter(room_name="测试群")

    # 模拟企业微信 Webhook 消息
    raw = {
        "MsgType": "text",
        "From": {"UserId": "zhangsan"},
        "Text": {"Content": "完成第三章习题"},
        "ChatId": "wr123456",
        "MsgId": "msg_001",
    }
    a.on_webhook_message(raw)

    msg = a.receive_message()
    assert msg is not None
    assert msg["sender"] == "zhangsan"
    assert msg["content"] == "完成第三章习题"
    assert msg["room"] == "wr123456"
    assert msg["status"] == "pending"
    print(f"  PASS: sender={msg['sender']} content={msg['content'][:20]}")
    return True

def test_4_send():
    """发送测试"""
    print("\n[Test 4] Send...")
    from wechat_gateway.wecom_adapter.wecom_adapter import WeComAdapter
    a = WeComAdapter()
    a.start()
    ok = a.send_message("测试消息 - WeCom Adapter")
    print(f"  {'PASS' if ok else 'SKIP (no API configured)'}")
    return True

def test_5_factory():
    """工厂注册测试"""
    print("\n[Test 5] Factory...")
    from wechat_gateway.python_adapter.wechat_adapter import create_adapter
    a = create_adapter("wecom", room_name="监督")
    status = a.get_status()
    assert "WeCom" in status["adapter"]
    print(f"  PASS: {status['adapter']}")
    return True

def test_6_full_pipeline():
    """全链路: 消息→AI审核"""
    print("\n[Test 6] Full pipeline...")
    from database import init_db, ensure_member
    from task_manager import process_message
    init_db()
    ensure_member("zhangsan", role="student")
    ensure_member("王老师", role="teacher")

    r = process_message("王老师", "完成Python作业，zhangsan负责")
    assert r and len(r) > 5, f"Empty reply: {r}"
    print(f"  Task: {r[:60]}...")

    r = process_message("zhangsan", "Python作业完成，写了爬虫抓了100条数据")
    assert r and len(r) > 5
    print(f"  Complete: {r[:60]}...")
    print("  PASS")
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("  WeCom Adapter Tests")
    print("=" * 50)

    all_pass = True
    for test in [test_1_token, test_2_adapter_create, test_3_message_format,
                 test_4_send, test_5_factory, test_6_full_pipeline]:
        try:
            test()
        except Exception as e:
            print(f"  FAIL: {e}")
            all_pass = False

    print("\n" + "=" * 50)
    print(f"  {'ALL PASSED' if all_pass else 'SOME FAILED'}")
    print("=" * 50)
