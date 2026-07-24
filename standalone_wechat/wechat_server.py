#!/usr/bin/env python3
"""
独立微信服务器 —— 在专用 Windows 设备上运行
包装旧版 pyautogui 微信操作，对外暴露 HTTP API
"""

import time, json, hashlib, threading, logging, sys, io, ctypes, os
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pyautogui, pyperclip
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.02

# ── Config ──
PORT = int(os.environ.get("WECHAT_SERVER_PORT", "8700"))
GROUP_NAME = os.environ.get("WECHAT_ROOM", "监督")
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "server.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("wechat_server")

# ── Windows API ──
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

def find_wechat(title="微信"):
    return user32.FindWindowW(None, title) or None

def to_screen(hwnd, cx, cy):
    pt = ctypes.wintypes.POINT(cx, cy)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    return (pt.x, pt.y)

# ── AttachThreadInput 前台切换 ──
class FgSwitch:
    def __init__(self):
        self.prev = self.attached = None
        self.wt = self.ct = 0
    def to(self, hwnd):
        self.prev = user32.GetForegroundWindow()
        if self.prev == hwnd: return
        self.ct = kernel32.GetCurrentThreadId()
        self.wt = user32.GetWindowThreadProcessId(self.prev, None)
        if self.ct != self.wt:
            self.attached = user32.AttachThreadInput(self.ct, self.wt, True)
            time.sleep(0.02)
        user32.SetForegroundWindow(hwnd); time.sleep(0.12)
        user32.BringWindowToTop(hwnd); time.sleep(0.08)
    def back(self):
        if self.prev and self.prev != user32.GetForegroundWindow():
            user32.SetForegroundWindow(self.prev)
        if self.attached:
            user32.AttachThreadInput(self.ct, self.wt, False)

# ── 微信操作 ──
class WeChatOperator:
    def __init__(self):
        self.hwnd = None
        self.fs = FgSwitch()
        self._saved_clip = self._saved_mouse = None

    def ok(self):
        self.hwnd = find_wechat()
        return self.hwnd is not None

    def _save(self):
        try: self._saved_clip = pyperclip.paste()
        except: pass
        self._saved_mouse = pyautogui.position()

    def _restore(self):
        if self._saved_mouse:
            pyautogui.moveTo(*self._saved_mouse)
        if self._saved_clip is not None:
            try: pyperclip.copy(self._saved_clip)
            except: pass

    def _size(self):
        r = ctypes.wintypes.RECT()
        user32.GetClientRect(self.hwnd, ctypes.byref(r))
        return r.right, r.bottom

    def open_group(self, name=GROUP_NAME):
        if not self.ok(): return False
        cw, ch = self._size()
        self._save()
        try:
            self.fs.to(self.hwnd)
            sx, sy = to_screen(self.hwnd, int(cw*0.07), int(ch*0.04))
            pyautogui.click(sx, sy); time.sleep(0.15)
            pyautogui.hotkey("ctrl","a"); time.sleep(0.03)
            pyautogui.press("backspace"); time.sleep(0.03)
            pyperclip.copy(name); pyautogui.hotkey("ctrl","v"); time.sleep(0.3)
            pyautogui.press("enter"); time.sleep(0.35)
            return True
        finally:
            self._restore(); self.fs.back()

    def read_message(self):
        if not self.ok(): return ""
        cw, ch = self._size()
        cx, cy = int(cw*0.28), int(ch*0.08)
        cw_a, ch_a = int(cw*0.68), int(ch*0.70)
        bottom = cy + ch_a - 10
        self._save()
        try:
            self.fs.to(self.hwnd)
            sx, sy = to_screen(self.hwnd, cx + cw_a//2, cy + ch_a//2)
            pyautogui.click(sx, sy); time.sleep(0.1)
            for _ in range(3):
                pyautogui.press("pagedown"); time.sleep(0.03)
            time.sleep(0.15)

            marker = f"__BM_{int(time.time())}__"
            pyperclip.copy(marker); time.sleep(0.03)

            for i in range(5):
                for rx in [0.15, 0.25, 0.35, 0.65, 0.75, 0.85, 0.2, 0.3, 0.7, 0.8]:
                    sx, sy = to_screen(self.hwnd, cx + int(cw_a*rx), bottom - i*40)
                    pyautogui.click(sx, sy, clicks=3, interval=0.03); time.sleep(0.04)
                    pyautogui.hotkey("ctrl","c"); time.sleep(0.04)
                    try: txt = pyperclip.paste()
                    except: txt = ""
                    if txt and txt != marker:
                        skip = ["ICP","腾讯","服务协议","隐私政策","经营许可证",
                               "icon","读屏","标签","无障碍","广播电视"]
                        if any(kw in txt for kw in skip): continue
                        dx, dy = to_screen(self.hwnd, cx + cw_a//2, cy - 10)
                        pyautogui.click(dx, dy)
                        return txt.strip()
        finally:
            self._restore(); self.fs.back()
        return ""

    def send(self, text):
        if not self.ok(): return
        cw, ch = self._size()
        self._save()
        try:
            self.fs.to(self.hwnd)
            sx, sy = to_screen(self.hwnd, int(cw*0.5), int(ch*0.93))
            pyautogui.click(sx, sy); time.sleep(0.05)
            pyperclip.copy(text); pyautogui.hotkey("ctrl","v"); time.sleep(0.06)
            pyautogui.press("enter")
        finally:
            self._restore(); self.fs.back()

# ── 消息队列 ──
wx = WeChatOperator()
msg_queue = []
queue_lock = threading.Lock()
last_msg_hash = None

# ── HTTP API ──
class APIHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        log.debug(f"HTTP {args}")

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
            room = body.get("room", GROUP_NAME)
            if not text:
                return self._json({"error": "text required"}, 400)
            wx.open_group(room)
            time.sleep(0.3)
            wx.send(text)
            log.info(f"[发送] {text[:60]}")
            self._json({"success": True})

        elif self.path == "/messages/mock":
            with queue_lock:
                msg_queue.append({
                    "id": f"m_{int(time.time())}",
                    "sender": body.get("sender", "?"),
                    "content": body.get("content", ""),
                    "room": body.get("room", GROUP_NAME),
                    "time": datetime.now().isoformat(),
                })
            self._json({"success": True})
        else:
            self._json({"error": "not found"}, 404)

# ── 轮询线程 ──
def poll_loop():
    global last_msg_hash
    log.info(f"开始轮询: {GROUP_NAME}")
    while True:
        try:
            if not wx.ok():
                time.sleep(5); continue
            wx.open_group()
            time.sleep(0.4)
            msg = wx.read_message()
            if msg:
                h = hashlib.md5(msg.encode()).hexdigest()
                if h != last_msg_hash:
                    last_msg_hash = h
                    with queue_lock:
                        msg_queue.append({
                            "id": f"m_{int(time.time())}",
                            "sender": "群成员",
                            "content": msg,
                            "room": GROUP_NAME,
                            "time": datetime.now().isoformat(),
                        })
                    log.info(f"[消息] {msg[:80]}")
        except Exception as e:
            log.error(f"轮询异常: {e}")
        time.sleep(5)

# ── 启动 ──
if __name__ == "__main__":
    print("=" * 50)
    print("  独立微信服务器")
    print("=" * 50)
    print(f"  API: http://0.0.0.0:{PORT}")
    print(f"  群聊: {GROUP_NAME}")
    print(f"  状态: /status | 消息: /messages | 发送: /send")
    print()

    if not wx.ok():
        print("  [WARN] 微信未运行! 请先打开微信")
        print()

    threading.Thread(target=poll_loop, daemon=True).start()
    server = HTTPServer(("0.0.0.0", PORT), APIHandler)
    print(f"  服务已启动: http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  停止...")
        server.shutdown()
