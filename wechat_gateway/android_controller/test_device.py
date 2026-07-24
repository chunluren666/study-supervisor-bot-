#!/usr/bin/env python3
"""设备连接测试 — 逐步验证 uiautomator2 连接"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import uiautomator2 as u2

print("=" * 50)
print("  UIAutomator2 设备连接测试")
print("=" * 50)

# Step 1: Connect
print("\n[1] 连接设备...")
d = u2.connect()
print(f"    设备: {d.info}")

# Step 2: Device info
print("\n[2] 设备信息:")
info = d.device_info
print(f"    SDK: {info.get('sdk', '?')}")
print(f"    分辨率: {d.window_size()}")

# Step 3: Get current app
print("\n[3] 当前前台应用:")
current = d.app_current()
print(f"    Package: {current.get('package', '?')}")
print(f"    Activity: {current.get('activity', '?')}")

# Step 4: Dump UI hierarchy
print("\n[4] 获取页面节点树...")
xml = d.dump_hierarchy()
print(f"    XML 长度: {len(xml)} 字符")
# Save
path = r"C:\Users\纪春堂\study-supervisor-bot\wechat_gateway\android_controller\wechat_page.xml"
with open(path, "w", encoding="utf-8") as f:
    f.write(xml)
print(f"    已保存: {path}")

# Step 5: Try to start WeChat
print("\n[5] 启动微信...")
d.app_start("com.tencent.mm")
import time; time.sleep(2)

current2 = d.app_current()
print(f"    Package: {current2.get('package', '?')}")

if "tencent" in current2.get("package", ""):
    print("    微信已打开!")
else:
    print("    可能未启动成功")

# Step 6: Check visible text elements
print("\n[6] 可见文本节点 (前20个):")
texts = []
for elem in d(className="android.widget.TextView"):
    try:
        t = elem.get_text()
        if t and len(t.strip()) > 0:
            texts.append(t.strip())
    except:
        pass

for i, t in enumerate(texts[:20], 1):
    print(f"    {i}. [{t[:60]}]")

print(f"\n    共找到 {len(texts)} 个文本节点")

# Step 7: Check for key WeChat elements
print("\n[7] 检查微信关键元素:")
for label, selector in [
    ("搜索", d(text="搜索")),
    ("通讯录", d(text="通讯录")),
    ("微信(tab)", d(text="微信")),
    ("发现", d(text="发现")),
    ("我", d(text="我")),
    ("输入框", d(className="android.widget.EditText")),
]:
    exists = selector.exists
    print(f"    {label}: {'有' if exists else '无'}")

print("\n" + "=" * 50)
print("  测试完成!")
print("=" * 50)
