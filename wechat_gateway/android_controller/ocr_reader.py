# -*- coding: utf-8 -*-
"""OCR 读取模块 — 截图 + 文字识别 (WeChat 自定义渲染元法通过节点树读取)"""

import logging, time, re
log = logging.getLogger("ocr_reader")

# 尝试加载 OCR 引擎
OCR_ENGINE = None

try:
    from cnocr import CnOcr
    OCR_ENGINE = CnOcr(rec_model_name='densenet_lite_136-gru')
    log.info("OCR: cnocr 已加载")
except ImportError:
    log.warning("cnocr 未安装, 尝试 easyocr...")
    try:
        import easyocr
        OCR_ENGINE = easyocr.Reader(['ch_sim', 'en'], gpu=False)
        log.info("OCR: easyocr 已加载")
    except ImportError:
        log.warning("无 OCR 引擎可用")


class OcrReader:
    """从截图提取文字"""

    def __init__(self, device):
        self.d = device

    def read_chat_messages(self, max_lines=10) -> list:
        """
        截取当前微信页面，OCR 识别所有可见文字
        返回: [(text, y_position), ...]  按屏幕位置从上到下排序
        """
        if OCR_ENGINE is None:
            return []

        try:
            img = self.d.screenshot()
            results = OCR_ENGINE.ocr(img)

            texts = []
            for r in results:
                text = r.get('text', '').strip() if isinstance(r, dict) else str(r[1]).strip()
                if text and len(text) > 1:
                    # 获取 y 坐标
                    pos = r.get('position', [[0,0]]) if isinstance(r, dict) else (r[0] if len(r) > 0 else [[0,0]])
                    if pos and len(pos) > 0 and len(pos[0]) > 1:
                        y = pos[0][0][1] if isinstance(pos[0][0], list) else 0
                    else:
                        y = 0
                    texts.append((text, y))

            # 按Y坐标排序(上到下)
            texts.sort(key=lambda x: x[1])
            return texts
        except Exception as e:
            log.error(f"OCR 失败: {e}")
            return []

    def get_last_message(self) -> str:
        """
        获取聊天页面最后一条对方消息。
        通过 y 坐标定位底部消息区域，过滤系统文字。
        """
        texts = self.read_chat_messages()
        if not texts:
            return ""

        # 过滤系统/状态栏文字
        skip_keywords = ["微信", "通讯录", "发现", "我", "搜索", "更多",
                         "电量", "充电", "台", "信号", "WiFi", "蓝牙"]
        filtered = [(t, y) for t, y in texts if not any(kw in t for kw in skip_keywords)]

        if not filtered:
            return ""

        # 底部区域消息: Y坐标在屏幕下半部分
        height = self.d.window_size()[1]
        bottom_msgs = [(t, y) for t, y in filtered if y > height * 0.4]

        if bottom_msgs:
            return bottom_msgs[-1][0]  # 最后一条
        return filtered[-1][0]  # fallback


# ── 测试 ──
if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    import uiautomator2 as u2

    print("=" * 40)
    print("  OCR 读取测试")
    print("=" * 40)

    d = u2.connect()
    reader = OcrReader(d)

    print("\n[1] 截屏 + OCR...")
    all_texts = reader.read_chat_messages()
    print(f"    识别到 {len(all_texts)} 段文字:")
    for t, y in all_texts:
        print(f"    y={y:4d} | {t[:60]}")

    print("\n[2] 提取最后一条消息...")
    last = reader.get_last_message()
    print(f"    最后消息: {last[:100] if last else '(无)'}")
