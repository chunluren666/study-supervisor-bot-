#!/usr/bin/env python3
"""Simple tunnel via localhost.run (SSH-based, no binary needed)"""

import subprocess, sys, os, time

print("=" * 50)
print("  公网隧道")
print("=" * 50)
print()
print("  运行方式 (选一个):")
print()
print("  方式1 - ssh 隧道 (Windows自带):")
print("    ssh -R 80:localhost:8000 nokey@localhost.run")
print()
print("  方式2 - bore (极简, 4MB):")
print("    浏览器打开: https://github.com/ekzhang/bore/releases")
print("    下载 bore-v0.5.2-x86_64-pc-windows-msvc.zip")
print("    解压后运行: bore.exe local 8000 --to bore.pub")
print()
print("  方式3 - 手动下载 cloudflared:")
print("    https://github.com/cloudflare/cloudflared/releases")
print()
print("  任选其一, 会得到公网URL → 填入企业微信后台")
print("=" * 50)

# Try SSH first (most systems have it)
print("\n尝试 SSH 隧道...")
try:
    r = subprocess.run(["ssh", "-V"], capture_output=True, text=True, timeout=5)
    print(f"  SSH: {r.stderr.strip()[:60]}")
    print("\n  运行: ssh -R 80:localhost:8000 nokey@localhost.run")
except:
    print("  SSH 不可用")
