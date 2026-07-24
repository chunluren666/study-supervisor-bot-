# -*- coding: utf-8 -*-
"""ADB 管理器 — 设备检测、连接、重连"""

import subprocess, time, logging
try:
    from .config import ADB_MODE, WIFI_DEVICE_IP
except ImportError:
    from config import ADB_MODE, WIFI_DEVICE_IP  # __main__ fallback

log = logging.getLogger("adb")


class AdbManager:
    """管理 ADB 连接和设备状态"""

    def __init__(self):
        self.connected = False
        self.device_id = None

    def connect(self) -> bool:
        """建立 ADB 连接"""
        if ADB_MODE == "wifi":
            return self._connect_wifi()
        return self._connect_usb()

    def _connect_usb(self) -> bool:
        """USB 连接"""
        log.info("尝试 USB ADB 连接...")
        out = self._adb("devices")
        for line in out.strip().split("\n")[1:]:
            if "\tdevice" in line:
                self.device_id = line.split("\t")[0]
                self.connected = True
                log.info(f"USB 已连接: {self.device_id}")
                return True
        log.warning("未检测到 USB 设备。请检查: USB调试是否开启? 数据线是否连接?")
        return False

    def _connect_wifi(self) -> bool:
        """WiFi ADB 连接"""
        log.info(f"尝试 WiFi ADB 连接: {WIFI_DEVICE_IP}")
        self._adb(f"connect {WIFI_DEVICE_IP}")
        time.sleep(2)
        out = self._adb("devices")
        for line in out.strip().split("\n")[1:]:
            if "\tdevice" in line and WIFI_DEVICE_IP in line:
                self.device_id = line.split("\t")[0]
                self.connected = True
                log.info(f"WiFi 已连接: {self.device_id}")
                return True
        log.warning(f"WiFi 连接失败: {WIFI_DEVICE_IP}")
        return False

    def reconnect(self) -> bool:
        """断线重连(最多3次)"""
        for i in range(3):
            log.info(f"重连尝试 {i+1}/3...")
            if self.connect():
                return True
            time.sleep(3)
        return False

    def check(self) -> bool:
        """检查连接是否存活"""
        if not self.connected:
            return False
        out = self._adb("devices")
        if str(self.device_id) in out and "device" in out:
            return True
        self.connected = False
        return False

    def status(self) -> dict:
        """获取设备信息"""
        if not self.check():
            return {"connected": False}
        model = self._adb("shell getprop ro.product.model").strip()
        android = self._adb("shell getprop ro.build.version.release").strip()
        return {
            "connected": True,
            "device_id": self.device_id,
            "model": model or "unknown",
            "android_version": android or "unknown",
            "mode": ADB_MODE,
        }

    def _adb(self, cmd: str) -> str:
        """执行 adb 命令"""
        try:
            r = subprocess.run(f"adb {cmd}", shell=True, capture_output=True,
                               text=True, timeout=15)
            return r.stdout + r.stderr
        except Exception as e:
            log.error(f"ADB 命令失败: {cmd} — {e}")
            return ""


# ── 测试 ──
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    adb = AdbManager()
    print("=" * 40)
    print("  ADB 连接测试")
    print("=" * 40)

    ok = adb.connect()
    print(f"\n连接: {'成功' if ok else '失败'}")
    print(f"状态: {adb.status()}")

    if ok:
        print("\n设备已就绪，可运行 android_controller.py")
    else:
        print("\n请检查:")
        print("  1. 手机: 设置 → 开发者选项 → USB调试 (开启)")
        print("  2. 手机: 连接后弹出授权框，点'允许'")
        print("  3. 电脑: adb devices 应显示设备")
