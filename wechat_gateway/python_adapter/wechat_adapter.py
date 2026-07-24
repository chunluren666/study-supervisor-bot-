# -*- coding: utf-8 -*-
"""
微信适配器 —— 抽象接口层

所有微信接入方案必须实现此接口。
当前默认使用 MockAdapter（模拟消息），
后续替换为 WeChatyAdapter 或 OpenClawAdapter。
"""

import abc
import json
import time
import logging
from pathlib import Path
from typing import Optional

LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


# ── 消息状态常量 ──
MSG_PENDING = "pending"        # 待处理
MSG_PROCESSING = "processing"  # 处理中
MSG_COMPLETED = "completed"    # 已完成


class BaseWechatAdapter(abc.ABC):
    """微信适配器抽象基类"""

    @abc.abstractmethod
    def receive_message(self) -> Optional[dict]:
        """
        获取一条待处理消息。
        返回格式:
          {
            "id": "msg_001",
            "sender": "张三",
            "content": "消息内容",
            "room": "监督",
            "time": "2026-07-23T10:30:00",
            "status": "pending"
          }
        无消息时返回 None。
        """
        pass

    @abc.abstractmethod
    def send_message(self, text: str, room: str = "") -> bool:
        """
        发送消息到指定群聊。
        返回 True/False 表示成功/失败。
        """
        pass

    @abc.abstractmethod
    def get_status(self) -> dict:
        """
        返回适配器状态:
          {"online": True/False, "adapter": "MockAdapter", "room": "监督"}
        """
        pass

    def start(self):
        """启动适配器（预留，子类可覆盖）"""
        pass

    def stop(self):
        """停止适配器（预留，子类可覆盖）"""
        pass


# ── 模拟适配器（不连真实微信） ──

class MockAdapter(BaseWechatAdapter):
    """
    模拟适配器 —— 用预设消息测试核心管线。
    不操作真实微信，纯本地测试。
    """

    def __init__(self, room_name: str = "监督"):
        self.room = room_name
        self.online = True
        self._message_id = 0

        # 预设测试消息队列
        self._queue = [
            {
                "id": "mock_001",
                "sender": "王老师",
                "content": "今天完成概率论第三章习题，明晚8点前提交，小明和小红负责",
                "room": room_name,
                "time": "2026-07-23T09:00:00",
                "status": MSG_PENDING,
            },
            {
                "id": "mock_002",
                "sender": "小明",
                "content": "完成了概率论习题，做了前5道，还有2道不太会",
                "room": room_name,
                "time": "2026-07-23T14:00:00",
                "status": MSG_PENDING,
            },
            {
                "id": "mock_003",
                "sender": "小红",
                "content": "完成了",
                "room": room_name,
                "time": "2026-07-23T15:00:00",
                "status": MSG_PENDING,
            },
        ]

        self.logger = logging.getLogger("mock_adapter")
        self.logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(LOG_DIR / "mock_adapter.log", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        self.logger.addHandler(fh)

    def receive_message(self) -> Optional[dict]:
        """从模拟队列取一条消息"""
        for msg in self._queue:
            if msg["status"] == MSG_PENDING:
                msg["status"] = MSG_PROCESSING
                self.logger.info(f"模拟消息: [{msg['sender']}] {msg['content'][:50]}")
                return msg
        return None

    def send_message(self, text: str, room: str = "") -> bool:
        """模拟发送，仅写日志"""
        target = room or self.room
        self.logger.info(f"[模拟发送 → {target}] {text[:80]}")
        print(f"\n  [模拟发送 → {target}]")
        print(f"  {text[:200]}\n")
        return True

    def get_status(self) -> dict:
        pending = sum(1 for m in self._queue if m["status"] == MSG_PENDING)
        return {
            "online": self.online,
            "adapter": "MockAdapter",
            "room": self.room,
            "pending_messages": pending,
        }

    def add_mock_message(self, sender: str, content: str):
        """手动添加测试消息"""
        self._message_id += 1
        self._queue.append({
            "id": f"mock_{self._message_id:03d}",
            "sender": sender,
            "content": content,
            "room": self.room,
            "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "status": MSG_PENDING,
        })
        self.logger.info(f"手动添加消息: [{sender}] {content[:50]}")


# ── WeChaty 适配器 ──

class WeChatyAdapter(BaseWechatAdapter):
    """
    WeChaty 适配器 —— 通过 HTTP 与 Node.js WeChaty 服务通信。
    消息状态由 Node.js 端的 /messages API 管理。
    """
    def __init__(self, gateway_url: str = "http://localhost:8800"):
        self.url = gateway_url.rstrip("/")
        self._room = None
        self._online = False

        self.logger = logging.getLogger("wechaty_adapter")
        self.logger.setLevel(logging.DEBUG)

        # HTTP client
        import urllib.request
        import urllib.error
        self._request = urllib.request

    def _get(self, path: str) -> dict:
        """GET 请求"""
        try:
            with self._request.urlopen(f"{self.url}{path}", timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            self.logger.error(f"GET {path} 失败: {e}")
            return {}

    def _post(self, path: str, data: dict) -> dict:
        """POST 请求"""
        try:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            req = self._request.Request(
                f"{self.url}{path}",
                data=body,
                headers={"Content-Type": "application/json"},
            )
            with self._request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            self.logger.error(f"POST {path} 失败: {e}")
            return {}

    def receive_message(self) -> Optional[dict]:
        """从网关获取一条 pending 消息"""
        result = self._get("/messages?status=pending&limit=1")
        messages = result.get("messages", [])
        if messages:
            return messages[0]
        return None

    def send_message(self, text: str, room: str = "") -> bool:
        """发送消息到指定群聊"""
        target = room or self._room or "监督"
        result = self._post("/send", {"room": target, "text": text})
        return result.get("success", False)

    def get_status(self) -> dict:
        """获取网关状态"""
        result = self._get("/status")
        self._online = result.get("online", False)
        self._room = result.get("room", self._room)
        return {
            "online": self._online,
            "adapter": "WeChatyAdapter",
            "room": self._room,
            "gateway": result,
        }

    def complete_message(self, msg_id: str):
        """标记消息为已完成"""
        import urllib.request
        body = json.dumps({"status": "completed"}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.url}/messages/{msg_id}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="PATCH",
        )
        try:
            with urllib.request.urlopen(req, timeout=5):
                pass
        except Exception:
            pass


# ── OpenClaw 适配器（占位，后续实现） ──

class OpenClawAdapter(BaseWechatAdapter):
    """
    OpenClaw 适配器 —— 预留接口。
    未来替换时只需实现此类，不改任何业务代码。
    """
    def __init__(self, **kwargs):
        pass

    def receive_message(self) -> Optional[dict]:
        pass

    def send_message(self, text: str, room: str = "") -> bool:
        pass

    def get_status(self) -> dict:
        pass


# ── 工厂函数 ──

def create_adapter(adapter_type: str = "mock", **kwargs) -> BaseWechatAdapter:
    """根据类型创建适配器"""
    # 延迟导入避免循环依赖
    adapters = {
        "mock": MockAdapter,
        "wechaty": WeChatyAdapter,
        "weilink": None,    # 按需加载
        "remote": None,     # 独立设备远程适配器
        "wecom": None,       # 企业微信自建应用
        "wecom_bot": None,   # 企业微信群机器人Webhook
        "openclaw": OpenClawAdapter,
    }
    if adapter_type not in adapters:
        raise ValueError(f"Unknown adapter type: {adapter_type}. Choose: {list(adapters.keys())}")

    if adapter_type == "weilink":
        from wechat_gateway.python_adapter.weilink_adapter import WeiLinkAdapter
        return WeiLinkAdapter(room_name=kwargs.get("room_name", "监督"))

    if adapter_type == "wecom":
        from wechat_gateway.wecom_adapter.wecom_adapter import WeComAdapter
        return WeComAdapter(room_name=kwargs.get("room_name", "监督"))

    if adapter_type == "wecom_bot":
        from wechat_gateway.wecom_bot.webhook_adapter import WeComBotAdapter
        return WeComBotAdapter()

    if adapter_type == "remote":
        from standalone_wechat.remote_adapter import RemoteWechatAdapter
        return RemoteWechatAdapter(
            server_url=kwargs.get("server_url", "http://192.168.1.100:8700"),
            room_name=kwargs.get("room_name", "监督"),
        )

    if adapter_type == "wechaty":
        return WeChatyAdapter(gateway_url=kwargs.get("gateway_url", "http://localhost:8800"))

    cls = adapters[adapter_type]
    return cls(**kwargs)
