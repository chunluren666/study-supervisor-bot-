# -*- coding: utf-8 -*-
"""企业微信连接测试"""

import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_1_config_loaded():
    """配置读取"""
    print("\n[Test 1] 配置读取...")
    from wechat_gateway.wecom_adapter.config import (
        WECOM_CORP_ID, WECOM_SECRET, WECOM_AGENT_ID
    )
    assert WECOM_CORP_ID, "WECOM_CORP_ID 为空, 请编辑 .env"
    assert WECOM_SECRET, "WECOM_SECRET 为空, 请编辑 .env"
    print(f"  CorpID: {WECOM_CORP_ID[:8]}...****")
    print(f"  Secret: ****")
    print(f"  AgentID: {WECOM_AGENT_ID}")
    return True

def test_2_token():
    """Token 获取"""
    print("\n[Test 2] Token 获取...")
    from wechat_gateway.wecom_adapter.wecom_api import WeComAPI
    api = WeComAPI()
    token = api.get_token()
    assert token, "Token 获取失败"
    print(f"  Token: {token[:15]}... OK")
    return True

def test_3_adapter_init():
    """适配器初始化"""
    print("\n[Test 3] 适配器初始化...")
    from wechat_gateway.wecom_adapter.wecom_adapter import WeComAdapter
    a = WeComAdapter(room_name="监督")
    a.start()
    s = a.get_status()
    assert s["online"], "适配器离线"
    assert "WeCom" in s["adapter"]
    print(f"  Status: {s['protocol']} - online={s['online']}")
    return True

def test_4_factory():
    """工厂注册"""
    print("\n[Test 4] 工厂注册...")
    from wechat_gateway.python_adapter.wechat_adapter import create_adapter
    a = create_adapter("wecom", room_name="监督")
    s = a.get_status()
    print(f"  {s['adapter']}: {s['protocol']}")
    assert "WeCom" in s["adapter"]
    return True

def test_5_send_test():
    """发送测试消息"""
    print("\n[Test 5] 发送测试...")
    from wechat_gateway.wecom_adapter.wecom_api import WeComAPI
    api = WeComAPI()
    r = api.send_text("WeCom 连接测试 - 学习监督机器人已上线")
    if r.get("errcode") == 0:
        print("  PASS: 消息已发送")
    else:
        print(f"  WARN: {r.get('errmsg', r)} (如无群聊则正常)")
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("  WeCom Connection Tests")
    print("=" * 50)

    from wechat_gateway.wecom_adapter.config import WECOM_CORP_ID, WECOM_SECRET
    if not WECOM_CORP_ID or not WECOM_SECRET:
        print("\n  [SKIP] 未配置 .env")
        print("  请在 .env 中填入:")
        print("    WECOM_CORP_ID=你的企业ID")
        print("    WECOM_SECRET=你的应用密钥")
        print("    WECOM_AGENT_ID=你的应用AgentID")
        import sys; sys.exit(0)

    all_pass = True
    for test in [test_1_config_loaded, test_2_token, test_3_adapter_init,
                 test_4_factory, test_5_send_test]:
        try:
            test()
        except Exception as e:
            print(f"  FAIL: {e}")
            all_pass = False

    print("\n" + "=" * 50)
    print(f"  {'ALL PASSED' if all_pass else 'SOME FAILED'}")
    print("=" * 50)
