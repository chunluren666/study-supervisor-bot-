# -*- coding: utf-8 -*-
"""
File Bridge — 零成本微信群接入
bridge_in.txt  → 你粘贴群消息
bridge_out.txt → 机器人写出回复
"""

import time
import logging
import sys
from pathlib import Path
from datetime import datetime

BRIDGE_DIR = Path(__file__).parent.parent
BRIDGE_IN = BRIDGE_DIR / "bridge_in.txt"
BRIDGE_OUT = BRIDGE_DIR / "bridge_out.txt"
LOG_FILE = BRIDGE_DIR / "logs" / "bridge.log"

# 消息过滤关键词（只处理包含这些词的消息）
PROCESS_KEYWORDS = [
    "任务", "完成", "学习", "提交", "截止", "作业", "考试",
    "复习", "预习", "笔记", "习题", "论文", "报告", "进度",
    "做了", "做完", "搞定", "@机器人", "@bot",
]


class FileBridge:
    """文件桥接器：轮询 bridge_in.txt → 处理 → 写入 bridge_out.txt"""

    def __init__(self, on_message):
        self.on_message = on_message
        self._last_pos = 0
        self._send_times = []       # 频率限制
        self._max_per_minute = 3     # 每分钟最多3条
        self.running = False

        # 日志
        self.logger = logging.getLogger("bridge")
        self.logger.setLevel(logging.DEBUG)
        LOG_FILE.parent.mkdir(exist_ok=True)
        fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        self.logger.addHandler(fh)
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
        self.logger.addHandler(sh)

        # 初始化文件
        for f in (BRIDGE_IN, BRIDGE_OUT):
            if not f.exists():
                f.write_text("", encoding="utf-8")

        self.logger.info(f"桥接就绪: {BRIDGE_IN} → {BRIDGE_OUT}")

    def start(self):
        self.running = True
        self._last_pos = BRIDGE_IN.stat().st_size
        try:
            while self.running:
                self._poll()
                time.sleep(3)
        except KeyboardInterrupt:
            self.running = False
        self.logger.info("桥接已停止")

    def stop(self):
        self.running = False

    def _poll(self):
        if not BRIDGE_IN.exists():
            return
        size = BRIDGE_IN.stat().st_size
        if size <= self._last_pos:
            return

        with open(BRIDGE_IN, "r", encoding="utf-8") as f:
            f.seek(self._last_pos)
            new_text = f.read()
        self._last_pos = size

        for line in new_text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue

            # 解析 "发送者: 内容"
            sender, content = "群成员", line
            if ": " in line and len(line.split(": ")[0]) <= 15:
                parts = line.split(": ", 1)
                sender, content = parts[0], parts[1]

            # 过滤
            if not self._should_process(content):
                self.logger.debug(f"过滤: {content[:50]}")
                continue

            self.logger.info(f"[{sender}] {content[:100]}")

            # 频率限制
            if not self._rate_ok():
                self.logger.warning("频率超限，跳过")
                continue

            # 处理
            try:
                reply = self.on_message(sender, content)
                if reply:
                    self._reply(reply)
            except Exception as e:
                self.logger.error(f"处理失败: {e}")

    def _should_process(self, content):
        if any(kw in content for kw in PROCESS_KEYWORDS):
            return True
        return False

    def _rate_ok(self):
        now = time.time()
        self._send_times = [t for t in self._send_times if now - t < 60]
        return len(self._send_times) < self._max_per_minute

    def _reply(self, text):
        self._send_times.append(time.time())
        ts = datetime.now().strftime("%m-%d %H:%M")
        line = f"\n[{ts}] {text}\n---\n"
        with open(BRIDGE_OUT, "a", encoding="utf-8") as f:
            f.write(line)
        self.logger.info(f"回复: {text[:80]}")


# ── 独立运行 ──
if __name__ == "__main__":
    sys.path.insert(0, str(BRIDGE_DIR))

    from database import init_db
    from task_manager import process_message

    init_db()

    print("=" * 50)
    print("  File Bridge — 微信群桥接模式")
    print("=" * 50)
    print(f"  输入文件: {BRIDGE_IN}")
    print(f"  输出文件: {BRIDGE_OUT}")
    print(f"  过滤规则: 只处理学习相关关键词")
    print(f"  频率限制: 每分钟最多3条回复")
    print()
    print("  使用方法:")
    print(f"  1. 打开 {BRIDGE_IN}")
    print(f"  2. 粘贴群消息 (格式: 张三: 今天完成XX)")
    print(f"  3. 保存文件")
    print(f"  4. 机器人自动处理，回复写入 {BRIDGE_OUT}")
    print(f"  5. 复制回复到微信群")
    print()
    print("  Ctrl+C 停止")
    print("=" * 50)

    bridge = FileBridge(on_message=process_message)
    bridge.start()
