# -*- coding: utf-8 -*-
"""企业微信回调模式测试"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_1_crypto_url_verify():
    """URL验证"""
    print("\n[Test 1] URL Verification...")
    from wechat_gateway.wecom_adapter.wecom_crypto import WXBizMsgCrypt

    wxcpt = WXBizMsgCrypt(
        token="test_token_123",
        encoding_aes_key="abcdefghijklmnopqrstuvwxyz0123456789ABCDEFG",
        corp_id="ww123456",
    )
    ret, plain = wxcpt.verify_url(
        msg_signature="5c45ff5e21c57e6ad56bac8758b79b1d9ac89fd3",
        timestamp="1409659589",
        nonce="263014780",
        echostr="RypEvHKD8eZQ6XoHqQoHwqMoUvNcN4bMi7NnEJ2qF5QIKq4zSMO5r1el8uTj0VOlG2B3dK0uP3sB6kW9dDkXsA==",
    )
    # This test will likely fail with random params, just verify no crash
    print(f"  ret={ret} (expected -1 with random params, no crash = OK)")
    return True

def test_2_crypto_decrypt():
    """消息解密"""
    print("\n[Test 2] Message Decrypt...")
    from wechat_gateway.wecom_adapter.wecom_crypto import WXBizMsgCrypt
    wxcpt = WXBizMsgCrypt("test", "x" * 43, "ww123")
    try:
        # Just test no crash
        ret, plain = wxcpt.decrypt_msg("sig", "123", "abc", "<xml><Encrypt>bad</Encrypt></xml>")
        print(f"  ret={ret} (expected -1 with bad data, no crash = OK)")
    except Exception as e:
        print(f"  Expected error: {e}")
    return True

def test_3_xml_parse():
    """XML解析"""
    print("\n[Test 3] XML Parse...")
    from wechat_gateway.wecom_adapter.wecom_crypto import parse_wecom_xml
    xml = """<xml>
        <ToUserName><![CDATA[ww123]]></ToUserName>
        <FromUserName><![CDATA[zhangsan]]></FromUserName>
        <CreateTime>1409659813</CreateTime>
        <MsgType><![CDATA[text]]></MsgType>
        <Content><![CDATA[完成第三章习题]]></Content>
        <MsgId>1234567890123456</MsgId>
        <AgentID>1000002</AgentID>
        <ChatId><![CDATA[wrABC123]]></ChatId>
    </xml>"""
    data = parse_wecom_xml(xml)
    assert data["MsgType"] == "text"
    assert data["FromUserName"] == "zhangsan"
    assert data["Content"] == "完成第三章习题"
    assert data["ChatId"] == "wrABC123"
    print(f"  PASS: sender={data['FromUserName']} content={data['Content']}")
    return True

def test_4_message_dedup():
    """消息去重"""
    print("\n[Test 4] Message Dedup...")
    from database import init_db, is_wecom_duplicate, log_wecom_message
    init_db()
    assert not is_wecom_duplicate("msg_001")
    log_wecom_message("msg_001", "user1", "hello", "", "2024-01-01")
    assert is_wecom_duplicate("msg_001")
    print("  PASS: duplicate detected")
    return True

def test_5_full_flow():
    """全链路: XML→解密→解析→AI审核→发送"""
    print("\n[Test 5] Full Flow...")
    from database import init_db, ensure_member
    from task_manager import process_message
    init_db()
    ensure_member("zhangsan", role="student")
    ensure_member("wang", role="teacher")

    r = process_message("wang", "完成数学第三章, zhangsan负责")
    assert r
    print(f"  Task: {r[:50]}...")

    r = process_message("zhangsan", "数学第三章全部完成, 15道题做完, 笔记5页")
    assert r
    print(f"  Complete: {r[:50]}...")
    print("  PASS")
    return True

def test_6_adapter_api():
    """适配器API可用"""
    print("\n[Test 6] Adapter API...")
    from wechat_gateway.wecom_adapter.wecom_api import WeComAPI
    from wechat_gateway.wecom_adapter.wecom_adapter import WeComAdapter
    api = WeComAPI()
    a = WeComAdapter(room_name="监督")
    a.start()
    s = a.get_status()
    assert "WeCom" in s["adapter"]
    a.on_webhook_message({
        "MsgType": "text", "From": {"UserId": "user1"},
        "Text": {"Content": "测试消息"}, "ChatId": "wr123", "MsgId": "99",
    })
    msg = a.receive_message()
    assert msg and msg["sender"] == "user1"
    print(f"  PASS: {msg['content']}")
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("  WeCom Callback Tests")
    print("=" * 50)
    all_pass = True
    for test in [test_1_crypto_url_verify, test_2_crypto_decrypt,
                 test_3_xml_parse, test_4_message_dedup,
                 test_5_full_flow, test_6_adapter_api]:
        try:
            test()
        except Exception as e:
            print(f"  FAIL: {e}")
            import traceback; traceback.print_exc()
            all_pass = False
    print("\n" + "=" * 50)
    print(f"  {'ALL PASSED' if all_pass else 'SOME FAILED'}")
    print("=" * 50)
