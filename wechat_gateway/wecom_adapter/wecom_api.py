# -*- coding: utf-8 -*-
"""企业微信官方 API 封装 — 无需桌面自动化"""

import json, time, logging, urllib.request, urllib.error
from .config import WECOM_CORP_ID, WECOM_SECRET, WECOM_AGENT_ID, WECOM_API_BASE

log = logging.getLogger("wecom_api")


class WeComAPI:
    """企业微信 API 客户端"""

    def __init__(self):
        self._token = None
        self._token_expires = 0

    # ── Token ──

    def get_token(self, force: bool = False) -> str:
        """获取 access_token (自动缓存, 失败自动重试)"""
        if not force and self._token and time.time() < self._token_expires:
            return self._token

        for attempt in range(3):
            url = f"{WECOM_API_BASE}/gettoken?corpid={WECOM_CORP_ID}&corpsecret={WECOM_SECRET}"
            try:
                with urllib.request.urlopen(url, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                if data.get("errcode") == 0:
                    self._token = data["access_token"]
                    self._token_expires = time.time() + data.get("expires_in", 7200) - 600
                    log.info(f"Token 刷新成功")
                    return self._token
                log.error(f"Token 错误: {data.get('errmsg', data)}")
            except Exception as e:
                log.error(f"Token 失败(尝试{attempt+1}/3): {e}")
            time.sleep(2 ** attempt)
        return ""

    # ── 内部 ──

    def _post(self, endpoint: str, body: dict) -> dict:
        token = self.get_token()
        if not token: return {"errcode": -1, "errmsg": "no token"}
        try:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                f"{WECOM_API_BASE}/{endpoint}?access_token={token}",
                data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            # Token 过期自动刷新重试
            if result.get("errcode") in (40001, 42001):
                log.info("Token 过期, 刷新重试...")
                token = self.get_token(force=True)
                if token:
                    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
                    req = urllib.request.Request(
                        f"{WECOM_API_BASE}/{endpoint}?access_token={token}",
                        data=data, headers={"Content-Type": "application/json"})
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        return json.loads(resp.read().decode("utf-8"))
            return result
        except Exception as e:
            return {"errcode": -1, "errmsg": str(e)}

    # ── 发送消息 ──

    def send_text(self, content: str, to_user: str = "@all", chat_id: str = "") -> dict:
        body = {"msgtype": "text", "agentid": WECOM_AGENT_ID, "text": {"content": content}}
        if chat_id: body["chatid"] = chat_id
        else: body["touser"] = to_user
        result = self._post("message/send", body)
        if result.get("errcode") == 0: log.info(f"已发送: {content[:60]}")
        else: log.error(f"发送失败: {result}")
        return result

    def send_image(self, media_id: str, chat_id: str = "") -> dict:
        """发送图片消息"""
        token = self.get_token()
        if not token: return {"errcode": -1}
        body = {"msgtype": "image", "agentid": WECOM_AGENT_ID, "image": {"media_id": media_id}}
        if chat_id: body["chatid"] = chat_id
        else: body["touser"] = "@all"
        return self._post("message/send", body)

    def send_file(self, media_id: str, chat_id: str = "") -> dict:
        """发送文件消息"""
        token = self.get_token()
        if not token: return {"errcode": -1}
        body = {"msgtype": "file", "agentid": WECOM_AGENT_ID, "file": {"media_id": media_id}}
        if chat_id: body["chatid"] = chat_id
        else: body["touser"] = "@all"
        return self._post("message/send", body)

    def send_markdown(self, content: str, chat_id: str = "") -> dict:
        """发送 Markdown 消息"""
        token = self.get_token()
        if not token:
            return {"errcode": -1}

        body = {
            "msgtype": "markdown",
            "agentid": WECOM_AGENT_ID,
            "markdown": {"content": content},
        }
        if chat_id:
            body["chatid"] = chat_id
        else:
            body["touser"] = "@all"

        try:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                f"{WECOM_API_BASE}/message/send?access_token={token}",
                data=data, headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"errcode": -1, "errmsg": str(e)}


# ── 测试 ──
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    api = WeComAPI()
    token = api.get_token()
    print(f"Token: {'OK' if token else 'FAILED'}")
    if token:
        r = api.send_text("WeCom API 测试消息", to_user="@all")
        print(f"Send: {r}")
