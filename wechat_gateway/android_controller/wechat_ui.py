# -*- coding: utf-8 -*-
"""WeChat UI — 稳定版: 滚动+去重+监控"""

import time, re, hashlib, logging
try:
    from .config import WECHAT_PACKAGE, TARGET_GROUP
except ImportError:
    from config import WECHAT_PACKAGE, TARGET_GROUP

log = logging.getLogger("wechat_ui")

SYS_WORDS = ["微信","通讯录","发现","我","搜索","充电","台","群聊","小程序","服务","动态","视频号","扫一扫","看一看","搜一搜","直播","购物","游戏"]


class WeChatUI:
    def __init__(self, device):
        self.d = device
        self.pkg = WECHAT_PACKAGE
        self._last_msg_hash = None
        self._msg_counter = 0

    # ── 状态检查 ──

    def is_foreground(self) -> bool:
        """微信是否在前台"""
        try:
            pkg = self.d.app_current().get("package", "")
            return self.pkg in pkg
        except Exception:
            return False

    def is_logged_in(self) -> bool:
        """是否已登录(通过检查页面元素)"""
        if not self.is_foreground():
            return False
        try:
            # 检查是否在登录页(有"登录"按钮)
            if self.d(text="登录").exists:
                return False
            if self.d(text="手机号登录").exists:
                return False
            return True
        except Exception:
            return False

    def ensure_foreground(self) -> bool:
        """检查微信是否在前台(Vivo不能自动切应用, 只检查不强制)"""
        if self.is_foreground() and self.is_logged_in():
            return True
        # Vivo/部分手机安全策略阻止ADB切应用, 仅尝试一次
        try:
            self.d.app_start(self.pkg)
            time.sleep(2)
        except Exception:
            pass
        return self.is_foreground()

    # ── 群聊导航 ──

    def open_group(self, name: str = None) -> bool:
        """打开指定群聊"""
        target = name or TARGET_GROUP
        if not self.ensure_foreground():
            return False

        # 确保在聊天列表
        for _ in range(2):
            self.d.press("back")
            time.sleep(0.2)

        # 查找并点击目标群
        group = self.d(text=target)
        if not group.exists:
            # 滚动查找
            w, h = self.d.window_size()
            self.d.swipe(w//2, h*2//3, w//2, h//3, duration=0.5)
            time.sleep(0.5)

        group = self.d(text=target)
        if group.exists:
            b = group.info.get("bounds", {})
            if b:
                cx = (b.get("left", 0) + b.get("right", 600)) // 2
                cy = (b.get("top", 0) + b.get("bottom", 100)) // 2
                self.d.click(cx, cy)
                time.sleep(1.5)
                log.info(f"已打开: {target}")
                return True

        log.warning(f"未找到: {target}")
        return False

    # ── 消息读取 (去重 + ID) ──

    def read_last_message(self) -> dict:
        """
        滚动到底部，读取最后一条消息。
        返回: {"id": "msg_xxx", "content": "...", "is_new": True/False}
        """
        if not self.is_foreground():
            return {}

        try:
            # 滚动到底部
            w, h = self.d.window_size()
            for _ in range(3):
                self.d.swipe(w//2, int(h*0.75), w//2, int(h*0.25), duration=0.3)
                time.sleep(0.3)

            # 读取所有可见文本
            xml = self.d.dump_hierarchy()
            texts = re.findall(r'text=\"([^\"]+)\"', xml)
            all_texts = [t.strip() for t in texts if t.strip() and len(t.strip()) > 1]

            # 过滤系统文字
            msgs = [t for t in all_texts if not any(s in t for s in SYS_WORDS)]
            # 过滤时间戳和百分比
            msgs = [m for m in msgs
                    if not re.match(r'^\d{1,2}:\d{2}$', m)
                    and not re.match(r'^\d+%$', m)
                    and len(m) > 2]

            if not msgs:
                return {}

            content = msgs[-1]  # 最后一条

            # 去重
            msg_hash = hashlib.md5(content.encode()).hexdigest()
            is_new = msg_hash != self._last_msg_hash
            if is_new:
                self._last_msg_hash = msg_hash
                self._msg_counter += 1

            return {
                "id": f"wx_{self._msg_counter}_{msg_hash[:8]}",
                "content": content,
                "is_new": is_new,
            }
        except Exception as e:
            log.error(f"读取失败: {e}")
            return {}

    # ── 消息发送 ──

    def send_message(self, text: str) -> bool:
        """发送消息到当前聊天"""
        try:
            inp = self.d(className="android.widget.EditText")
            if not inp.exists:
                log.warning("未找到输入框")
                return False
            inp.click()
            time.sleep(0.2)
            inp.set_text(text)
            time.sleep(0.3)

            send = self.d(text="发送")
            if not send.exists:
                send = self.d(description="发送")
            if send.exists:
                send.click()
                log.info(f"已发送: {text[:60]}")
                return True
            else:
                import subprocess
                subprocess.run("adb shell input tap 1100 2400", shell=True)
                return True
        except Exception as e:
            log.error(f"发送失败: {e}")
            return False

    # ── 异常恢复 ──

    def recover(self) -> bool:
        """尝试恢复微信状态"""
        log.info("尝试恢复...")
        try:
            self.d.app_stop(self.pkg)
            time.sleep(1)
            self.d.app_start(self.pkg)
            time.sleep(2)
            return self.is_foreground() and self.is_logged_in()
        except Exception:
            return False
