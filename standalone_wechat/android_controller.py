#!/usr/bin/env python3
"""
Android 微信控制器 —— 通过 uiautomator2 + ADB 操控手机微信
运行在连接了 Android 手机的电脑上(可旧笔记本)
对外暴露 HTTP API 供 AI 监督系统调用
"""

import time, json, hashlib, threading, logging, sys, io, os
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PORT = int(os.environ.get("WECHAT_SERVER_PORT", "8700"))
GROUP_NAME = os.environ.get("WECHAT_ROOM", "监督")
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_DIR / "android.log", encoding='utf-8'),
              logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger("android_wx")

# ── 尝试连接 uiautomator2 ──
try:
    import uiautomator2 as u2
    d = u2.connect()  # USB连接, 或 u2.connect('192.168.1.x') WiFi连接
    log.info(f"设备已连接: {d.info}")
    HAS_U2 = True
except Exception as e:
    log.warning(f"uiautomator2 未连接: {e}")
    log.warning("请先安装: pip install uiautomator2 && python -m uiautomator2 init")
    HAS_U2 = False

# ── 微信操作 ──
class AndroidWeChat:
    """通过 uiautomator2 操作手机微信"""

    def __init__(self):
        self.pkg = "com.tencent.mm"

    def ok(self):
        return HAS_U2 and d is not None

    def open_group(self, name=GROUP_NAME):
        if not self.ok(): return False
        try:
            d.app_start(self.pkg)
            time.sleep(1.5)
            # 点击搜索
            d(text="搜索").click()
            time.sleep(0.3)
            # 输入群名
            d(className="android.widget.EditText").set_text(name)
            time.sleep(1)
            # 点击搜索结果
            d(text=name).click()
            time.sleep(1)
            log.info(f"已打开群: {name}")
            return True
        except Exception as e:
            log.error(f"打开群失败: {e}")
            return False

    def read_message(self):
        """读取最后一条消息文字"""
        if not self.ok(): return ""
        try:
            # 点击聊天区域底部, 然后找最后一条文本消息
            msgs = d(className="android.widget.TextView")
            texts = []
            for m in msgs[-10:]:  # 最近10条
                t = m.get_text()
                if t and len(t) > 1:
                    texts.append(t)
            return texts[-1] if texts else ""
        except Exception as e:
            log.error(f"读取失败: {e}")
            return ""

    def send(self, text):
        if not self.ok(): return
        try:
            # 点击输入框
            d(className="android.widget.EditText").click()
            time.sleep(0.2)
            d.send_keys(text)
            time.sleep(0.2)
            # 点击发送
            d(text="发送").click()
            log.info(f"已发送: {text[:60]}")
        except Exception as e:
            log.error(f"发送失败: {e}")

# ── 全局实例 ──
wx = AndroidWeChat()
msg_queue = []
queue_lock = threading.Lock()
last_msg_hash = None

# ── HTTP API ──
class APIHandler(BaseHTTPRequestHandler):
    def log_message(self, f, *a): pass

    def _json(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_GET(self):
        if self.path == "/status":
            self._json({"online": wx.ok(), "queue_size": len(msg_queue)})
        elif self.path == "/messages":
            with queue_lock:
                msgs = list(msg_queue)
                msg_queue.clear()
            self._json({"messages": msgs})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        if self.path == "/send":
            text = body.get("text", "")
            if not text: return self._json({"error": "text required"}, 400)
            wx.open_group()
            time.sleep(0.5)
            wx.send(text)
            self._json({"success": True})
        elif self.path == "/messages/mock":
            with queue_lock:
                msg_queue.append({
                    "id": f"m_{int(time.time())}", "sender": body.get("sender", "?"),
                    "content": body.get("content", ""),
                    "room": body.get("room", GROUP_NAME),
                    "time": datetime.now().isoformat(),
                })
            self._json({"success": True})
        else:
            self._json({"error": "not found"}, 404)

# ── 轮询 ──
def poll():
    global last_msg_hash
    log.info(f"轮询开始: {GROUP_NAME}")
    while True:
        try:
            if not wx.ok(): time.sleep(5); continue
            wx.open_group()
            time.sleep(0.5)
            msg = wx.read_message()
            if msg:
                h = hashlib.md5(msg.encode()).hexdigest()
                if h != last_msg_hash:
                    last_msg_hash = h
                    with queue_lock:
                        msg_queue.append({
                            "id": f"m_{int(time.time())}", "sender": "群成员",
                            "content": msg, "room": GROUP_NAME,
                            "time": datetime.now().isoformat(),
                        })
                    log.info(f"[消息] {msg[:80]}")
        except Exception as e:
            log.error(f"轮询异常: {e}")
        time.sleep(5)

# ── 启动 ──
if __name__ == "__main__":
    print("=" * 50)
    print("  Android 微信服务器")
    print("=" * 50)
    print(f"  API: http://0.0.0.0:{PORT}")
    print(f"  uiautomator2: {'已连接' if HAS_U2 else '未连接!'}")
    print(f"  安装: pip install uiautomator2")
    print(f"  初始化: python -m uiautomator2 init")
    print()

    threading.Thread(target=poll, daemon=True).start()
    HTTPServer(("0.0.0.0", PORT), APIHandler).serve_forever()
