# -*- coding: utf-8 -*-
"""
Gewechat 适配器 — iPad协议 Docker部署, 原生 REST API
部署: docker run -d -p 2531:2531 -p 2532:2532 gewe/gewe
"""

import json, logging, time, urllib.request, urllib.error, sys, io, base64
from pathlib import Path
from typing import Optional

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


class GewechatAdapter:
    """
    Gewechat iPad 协议适配器
    实现 BaseWechatAdapter 兼容接口
    Docker 部署后即可使用, 免费, 无需手机 Root
    """

    def __init__(self, server_url: str = "http://192.168.1.100:2531",
                 room_name: str = "监督"):
        self.url = server_url.rstrip("/")
        self.room = room_name
        self.token = None
        self.app_id = None
        self._logged_in = False
        self._msg_queue = []
        self._cursor = ""

        self.logger = logging.getLogger("gewechat")
        self.logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(LOG_DIR / "gewechat.log", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        self.logger.addHandler(fh)

    def _api(self, endpoint: str, data: dict = None) -> dict:
        """调用 Gewechat API"""
        url = f"{self.url}/v2/api/{endpoint}"
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["X-GEWE-TOKEN"] = self.token

        try:
            body = json.dumps(data or {}, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(url, data=body, headers=headers,
                                         method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            self.logger.error(f"API {endpoint}: {e}")
            return {"ret": -1, "msg": str(e)}

    # ── 登录 ──
    def login(self):
        """获取token → 获取二维码 → 等待扫码"""
        # 1. Token
        r = self._api("tools/getTokenId")
        if r.get("ret") != 200:
            raise Exception(f"Token 失败: {r}")

        self.token = r["data"]
        self.logger.info(f"Token: {self.token[:20]}...")

        # 2. 二维码
        r = self._api("login/getLoginQrCode")
        if r.get("ret") != 200:
            raise Exception(f"QR 失败: {r}")

        qr_data = r["data"]
        self.app_id = qr_data["appId"]
        qr_img = base64.b64decode(qr_data["qrImgBase64"])

        # 保存二维码图片
        qr_path = LOG_DIR / "gewechat_qr.png"
        qr_path.write_bytes(qr_img)
        print(f"\n  二维码已保存: {qr_path}")
        print(f"  或用 URL: {qr_data.get('qrData', '')}")
        print(f"  请用微信小号扫描登录...")

        # 3. 等待扫码确认
        uuid = qr_data["uuid"]
        for i in range(60):
            time.sleep(3)
            r = self._api("login/checkQr", {"appId": self.app_id, "uuid": uuid})
            ret = r.get("ret", -1)
            if ret == 200:
                self._logged_in = True
                self.logger.info("登录成功!")
                return True
        raise Exception("扫码超时")

    # ── 接口 ──
    def receive_message(self) -> Optional[dict]:
        """同步消息"""
        if not self._logged_in:
            return None
        r = self._api("message/syncMessage", {"appId": self.app_id})
        msgs = r.get("data", {}).get("msgs", [])
        for m in msgs:
            sender = m.get("fromUserName", "?")
            content = m.get("content", "") or m.get("pushContent", "")
            return {
                "id": str(m.get("newMsgId", "")),
                "sender": sender,
                "content": content,
                "room": m.get("fromUserName", ""),
                "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
        return None

    def send_message(self, text: str, room: str = "") -> bool:
        if not self._logged_in:
            return False
        target = room or self.room
        r = self._api("message/postText", {
            "appId": self.app_id,
            "toWxid": target,
            "content": text,
        })
        return r.get("ret") == 200

    def get_status(self) -> dict:
        return {
            "online": self._logged_in,
            "adapter": "GewechatAdapter",
            "protocol": "iPad",
            "server": self.url,
        }
