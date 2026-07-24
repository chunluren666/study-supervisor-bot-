#!/usr/bin/env python3
"""Android 微信控制器 — HTTP API 服务"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import json, time, threading, logging, re
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

try:
    from .config import SERVER_PORT, TARGET_GROUP, RATE_LIMIT_SECONDS, RATE_LIMIT_MAX, POLL_INTERVAL
    from .wechat_ui import WeChatUI
except ImportError:
    from config import SERVER_PORT, TARGET_GROUP, RATE_LIMIT_SECONDS, RATE_LIMIT_MAX, POLL_INTERVAL
    from wechat_ui import WeChatUI

import uiautomator2 as u2

# ── 日志 ──
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "android_controller.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("controller")

# ── 全局 ──
device = u2.connect()
ui = WeChatUI(device)
msg_queue = []
queue_lock = threading.Lock()
send_times = []


def get_status_dict():
    """生成完整状态"""
    try:
        in_wechat = ui.is_foreground()
        logged_in = ui.is_logged_in() if in_wechat else False
    except Exception:
        in_wechat, logged_in = False, False

    return {
        "online": in_wechat and logged_in,
        "wechat_foreground": in_wechat,
        "wechat_logged_in": logged_in,
        "device": {
            "model": device.info.get("productName", "?"),
            "screen": f'{device.info.get("displayWidth",0)}x{device.info.get("displayHeight",0)}',
            "screen_on": device.info.get("screenOn", False),
        },
        "queue_size": len(msg_queue),
        "target_group": TARGET_GROUP,
    }


# ── HTTP API ──
class API(BaseHTTPRequestHandler):
    def log_message(self, f, *a): pass

    def _json(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_GET(self):
        if self.path == "/status":
            self._json(get_status_dict())
        elif self.path == "/messages":
            with queue_lock:
                msgs = list(msg_queue)
                msg_queue.clear()
            self._json({"messages": msgs})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = json.loads(self.rfile.read(length)) if length else {}

        if self.path == "/send":
            text = body.get("text", "")
            room = body.get("room", TARGET_GROUP)
            if not text:
                return self._json({"error": "text required"}, 400)

            # 频率限制
            now = time.time()
            global send_times
            send_times = [t for t in send_times if now - t < RATE_LIMIT_SECONDS]
            if len(send_times) >= RATE_LIMIT_MAX:
                return self._json({"success": False, "error": "rate limited"})
            send_times.append(now)

            if room != TARGET_GROUP:
                ui.open_group(room)
                time.sleep(0.5)
            sent = ui.send_message(text)
            self._json({"success": sent})


# ── 轮询 ──
def health_monitor():
    """健康监控：Vivo不强制切应用, 仅报告"""
    warned = False
    while True:
        try:
            if not device.info.get("screenOn"):
                log.warning("屏幕关闭! 请手动解锁")
            elif not ui.is_foreground():
                if not warned:
                    log.warning("微信不在前台! 请手动打开微信并保持在前台")
                    warned = True
            else:
                warned = False
        except Exception as e:
            log.error(f"健康检查异常: {e}")
        time.sleep(30)

def poll_loop():
    """轮询消息"""
    log.info(f"轮询开始: {TARGET_GROUP} ({POLL_INTERVAL}s)")

    while True:
        try:
            if not ui.is_foreground():
                time.sleep(POLL_INTERVAL)
                continue

            if not ui.open_group():
                time.sleep(POLL_INTERVAL)
                continue

            result = ui.read_last_message()
            if result and result.get("is_new") and result.get("content"):
                with queue_lock:
                    msg_queue.append({
                        "id": result["id"],
                        "sender": "群成员",
                        "content": result["content"],
                        "room": TARGET_GROUP,
                        "time": datetime.now().isoformat(),
                    })
                log.info(f"[消息] {result['content'][:100]}")

        except Exception as e:
            log.error(f"轮询异常: {e}")
        time.sleep(POLL_INTERVAL)


# ── 启动 ──
if __name__ == "__main__":
    print("=" * 50)
    print("  Android 微信控制器 v2")
    print("=" * 50)
    print(f"  API:      http://0.0.0.0:{SERVER_PORT}")
    print(f"  群聊:     {TARGET_GROUP}")
    print(f"  设备:     {device.info.get('productName', '?')}")
    print(f"  屏幕:     {device.info.get('screenOn', False)}")
    print()

    # Vivo: 不强制切应用, 依赖用户手动打开微信
    if not ui.is_foreground():
        log.warning("请手动打开微信并保持在前台!")

    threading.Thread(target=health_monitor, daemon=True).start()
    threading.Thread(target=poll_loop, daemon=True).start()

    server = HTTPServer(("0.0.0.0", SERVER_PORT), API)
    print(f"  服务已启动\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  停止...")
        server.shutdown()
