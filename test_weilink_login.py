#!/usr/bin/env python3
"""WeiLink 登录测试 v2 - 直接用 recv() 轮询"""
import sys, time, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r"C:\Users\纪春堂\study-supervisor-bot")

from weilink import WeiLink

print("=" * 50)
print("  WeiLink 登录测试 v2")
print("=" * 50)

wl = WeiLink()

# 登录
print("\n请用微信小号扫码...\n")
bot_info = wl.login()
print(f"\n登录成功! Bot ID: {bot_info.bot_id}")

# 启动后台
wl.run_background()
print("后台运行中...")
print("\n请给机器人发送: 测试机器人收到吗？")
print("按 Ctrl+C 停止\n")

# 直接用 recv() 轮询
try:
    while True:
        msgs = wl.recv(timeout=5.0)
        if msgs:
            for msg in msgs:
                sender = getattr(msg, 'from_user', '?')
                text = (getattr(msg, 'text', None) or '').strip()
                msg_id = getattr(msg, 'message_id', 0)
                print(f"\n>>> [{msg_id}] {sender}: {text}")

                if "测试" in text:
                    reply = f"[bot] 收到! (msg {msg_id})"
                    print(f"<<< {reply}")
                    wl.send(sender, reply)

        # 也检查是否有 pending 的 get_updates
        time.sleep(1)
except KeyboardInterrupt:
    print("\n停止...")
finally:
    wl.stop()
