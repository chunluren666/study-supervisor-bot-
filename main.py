#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习监督机器人 - 主入口

启动方式:
  python main.py                # 模拟模式（不连微信，测试管线）
  python main.py --live         # 真实模式（连接 WeChaty 网关）
  python main.py --web          # Web 仪表盘
  python main.py --add-msg      # 交互式添加模拟消息
"""

import sys
import time
import argparse
import logging

from config import (
    WECHAT_GATEWAY_MODE, WECHAT_GATEWAY_URL, WECHAT_GROUP_NAME,
    WECHAT_POLL_INTERVAL, ADMIN_USERS, LOG_LEVEL, LOG_FILE,
)

# 部署模式: local 或 production
WECOM_DEPLOY_MODE = __import__('os').environ.get("WECOM_DEPLOY_MODE", "local")
from database import init_db
from task_manager import process_message, generate_reminders, generate_stats_report
from scheduler import Scheduler
from runtime_stats import msg_received, msg_sent, msg_failed, health_update, get_summary, get_weekly_report
from wechat_gateway.python_adapter.wechat_adapter import (
    create_adapter, MockAdapter, BaseWechatAdapter,
)

# ── 日志 ──
def setup_logging():
    logger = logging.getLogger("main")
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    return logger

logger = setup_logging()

# ── 全局适配器 ──
adapter: BaseWechatAdapter = None


def send_reply(text: str, room: str = ""):
    """发送回复到微信群"""
    target = room or WECHAT_GROUP_NAME
    if adapter:
        adapter.send_message(text, target)
        logger.info(f"[发送 → {target}] {text[:80]}")


def poll_messages():
    """轮询消息 → 处理 → 回复"""
    msg = adapter.receive_message()
    if not msg:
        return False

    sender = msg.get("sender", "未知")
    content = msg.get("content", "")
    msg_id = msg.get("id", "")

    msg_received()
    logger.info(f"[{sender}] {content[:100]}")

    try:
        reply = process_message(sender, content)
        if reply:
            send_reply(reply)
            msg_sent()
            if hasattr(adapter, 'complete_message'):
                adapter.complete_message(msg_id)
            return True
        msg_failed()
    except Exception as e:
        msg_failed()
        logger.error(f"处理消息失败: {e}")

    return False


# ── Web API ──

def create_web_app():
    from fastapi import FastAPI, Query
    from fastapi.responses import HTMLResponse
    from database import list_members, get_pending_tasks, get_all_stats, ensure_member, get_db
    from task_manager import do_spot_check, generate_stats_report, generate_reminders
    from study_score import calculate_all_scores

    app = FastAPI(title="学习监督机器人", version="2.0")
    BASE_DIR = __import__('config').BASE_DIR

    @app.get("/")
    def root():
        return {"status": "running", "adapter": adapter.get_status() if adapter else {}}

    # ── 企业微信回调 ──
    @app.get("/wecom/callback")
    def wecom_verify(msg_signature: str = "", timestamp: str = "",
                     nonce: str = "", echostr: str = ""):
        """企业微信 URL 验证 — 必须返回纯文本"""
        from fastapi.responses import PlainTextResponse
        if not all([msg_signature, timestamp, nonce, echostr]):
            return PlainTextResponse("missing params")
        from wechat_gateway.wecom_adapter.wecom_crypto import WXBizMsgCrypt
        from wechat_gateway.wecom_adapter.config import (
            WECOM_TOKEN, WECOM_ENCODING_AES_KEY, WECOM_CORP_ID,
        )
        try:
            wxcpt = WXBizMsgCrypt(WECOM_TOKEN or "test", WECOM_ENCODING_AES_KEY or "x"*43, WECOM_CORP_ID or "ww")
            ret, plain = wxcpt.verify_url(msg_signature, timestamp, nonce, echostr)
            if ret == 0:
                return PlainTextResponse(plain)
        except Exception:
            pass
        return PlainTextResponse("")

    @app.post("/wecom/callback")
    async def wecom_receive(request: __import__('fastapi').Request):
        """企业微信消息回调"""
        from wechat_gateway.wecom_adapter.wecom_crypto import WXBizMsgCrypt, parse_wecom_xml
        from wechat_gateway.wecom_adapter.config import (
            WECOM_TOKEN, WECOM_ENCODING_AES_KEY, WECOM_CORP_ID,
        )
        from database import is_wecom_duplicate, log_wecom_message

        msg_signature = request.query_params.get("msg_signature", "")
        timestamp = request.query_params.get("timestamp", "")
        nonce = request.query_params.get("nonce", "")
        body = await request.body()

        try:
            wxcpt = WXBizMsgCrypt(WECOM_TOKEN or "test", WECOM_ENCODING_AES_KEY or "x"*43, WECOM_CORP_ID or "ww")
            ret, plain = wxcpt.decrypt_msg(msg_signature, timestamp, nonce, body.decode())
            if ret != 0:
                return "decrypt failed"

            data = parse_wecom_xml(plain)
            msg_id = data.get("MsgId", "")
            msg_type = data.get("MsgType", "")
            user_id = data.get("FromUserName", "")
            content = data.get("Content", "").strip()
            chat_id = data.get("ChatId", "")

            if msg_type != "text" or not content:
                return "ok"

            if is_wecom_duplicate(msg_id):
                return "ok"

            log_wecom_message(msg_id, user_id, content, str(body), timestamp)

            # 直接处理消息
            if msg_type == "text" and content:
                from runtime_stats import msg_received, msg_sent, msg_failed
                msg_received()
                logger.info(f"[WeCom] {user_id}: {content[:100]}")
                try:
                    reply = process_message(user_id, content)
                    if reply:
                        if adapter and hasattr(adapter, 'send_message'):
                            # 根据chat_id决定发群还是发个人
                            if chat_id:
                                adapter.send_message(reply, room=chat_id)
                            else:
                                adapter.send_message(reply)
                        msg_sent()
                except Exception as e2:
                    msg_failed()
                    logger.error(f"处理失败: {e2}")

        except Exception as e:
            logger.error(f"WeCom callback error: {e}")

        return "ok"

    @app.get("/wecom/refresh")
    def wecom_refresh():
        """强制刷新 WeChat Token"""
        from wechat_gateway.wecom_adapter.wecom_api import WeComAPI
        api = WeComAPI()
        token = api.get_token(force=True)
        return {"token_ok": bool(token), "token_preview": token[:15] + "..." if token else "FAILED"}

    @app.get("/myip")
    def myip():
        """诊断: 显示本机出站 IP"""
        import urllib.request
        try:
            ip = urllib.request.urlopen("https://api.ipify.org", timeout=5).read().decode()
        except:
            ip = "unknown"
        return {"outbound_ip": ip}

    @app.get("/dashboard", response_class=HTMLResponse)
    def dashboard():
        tpl = BASE_DIR / "templates" / "dashboard.html"
        return tpl.read_text(encoding="utf-8") if tpl.exists() else "<h1>Not found</h1>"

    @app.get("/api/dashboard")
    def api_dashboard():
        tasks = get_pending_tasks()
        db = get_db()
        enriched = []
        for t in tasks:
            rows = db.execute(
                "SELECT ta.*, m.wx_name FROM task_assignees ta "
                "JOIN members m ON ta.member_id = m.id WHERE ta.task_id = ?", (t["id"],)
            ).fetchall()
            for r in rows:
                enriched.append({**t, "wx_name": r["wx_name"],
                    "assignee_status": r["status"], "answer": r["answer"] or "",
                    "ai_audit_reason": r["ai_audit_reason"] or ""})
        db.close()
        db2 = get_db()
        audits = db2.execute(
            "SELECT ce.*, m.wx_name FROM completion_evidence ce "
            "JOIN task_assignees ta ON ce.assignee_id = ta.id "
            "JOIN members m ON ta.member_id = m.id "
            "ORDER BY ce.submitted_at DESC LIMIT 20"
        ).fetchall()
        db2.close()

        from risk_analyzer import assess_all as assess_risks
        from database import get_all_risks
        risks = get_all_risks()

        return {"tasks": enriched, "audits": [dict(a) for a in audits],
                "scores": calculate_all_scores(),
                "risks": risks}

    @app.get("/members")
    def api_members():
        return list_members()

    @app.get("/tasks")
    def api_tasks():
        return get_pending_tasks()

    @app.get("/tasks/{member}")
    def api_member_tasks(member: str):
        return get_tasks_by_member(member)

    @app.get("/stats")
    def api_stats():
        return get_all_stats()

    @app.get("/stats/{member}")
    def api_member_stats(member: str):
        from database import get_member_stats
        return get_member_stats(member)

    @app.post("/spot-check")
    def api_spot_check(member: str = Query(...)):
        mid = ensure_member(member)
        msg = do_spot_check(member, mid)
        if msg:
            send_reply(msg)
        return {"message": msg}

    @app.post("/remind")
    def api_remind():
        reminders = generate_reminders()
        for r in reminders:
            send_reply(r[2])
        return {"reminders": [r[2] for r in reminders]}

    @app.post("/stats-report")
    def api_stats_report():
        report = generate_stats_report()
        send_reply(report)
        return {"report": report}

    @app.get("/api/runtime")
    def api_runtime():
        """运行统计"""
        return get_summary()

    @app.get("/api/runtime/weekly")
    def api_runtime_weekly():
        return get_weekly_report()

    return app


# ── 交互式添加模拟消息 ──

def interactive_mock():
    """交互式添加模拟消息"""
    if not isinstance(adapter, MockAdapter):
        print("仅 Mock 模式支持此功能")
        return

    print("\n=== 交互式模拟消息 ===")
    print("输入消息内容，机器人会实时处理。输入 q 退出。\n")

    while True:
        try:
            content = input("消息内容 > ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if content.lower() == 'q':
            break
        if not content:
            continue

        sender = input("发送者 (默认: 群成员) > ").strip() or "群成员"
        adapter.add_mock_message(sender, content)
        poll_messages()


# ── 入口 ──

def main():
    global adapter

    parser = argparse.ArgumentParser(description="学习监督机器人")
    parser.add_argument("--live", action="store_true", help="真实微信模式")
    parser.add_argument("--web", action="store_true", help="Web API 模式")
    parser.add_argument("--add-msg", action="store_true", help="添加模拟消息")
    parser.add_argument("--wecom-test", action="store_true", help="测试企业微信连接")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    # ── 企业微信测试模式 ──
    if args.wecom_test:
        from wechat_gateway.wecom_adapter.wecom_api import WeComAPI
        from wechat_gateway.wecom_adapter.config import WECOM_CORP_ID, WECOM_SECRET, WECOM_AGENT_ID
        print("=" * 50)
        print("  企业微信连接测试")
        print("=" * 50)
        if not WECOM_CORP_ID or not WECOM_SECRET:
            print("  [ERROR] 企业微信未配置!")
            print("  请在 .env 中填入 WECOM_CORP_ID 和 WECOM_SECRET")
            print("  详见: WE_COM_SETUP.md")
            return
        print(f"  CorpID: {WECOM_CORP_ID[:15]}...")
        print(f"  Secret: ***")
        print(f"  AgentID: {WECOM_AGENT_ID}")
        api = WeComAPI()
        print("\n  [1] 获取 Token...")
        token = api.get_token()
        if token:
            print(f"  [OK] Token: {token[:15]}...")
        else:
            print("  [FAIL] Token 获取失败")
            return
        print("\n  [2] 发送测试消息...")
        r = api.send_text("学习监督机器人已上线 - WeCom 连接测试成功")
        if r.get("errcode") == 0:
            print("  [OK] 消息发送成功!")
        else:
            print(f"  [FAIL] {r}")
        return

    # ── WeCom 模式配置检查 ──
    if WECHAT_GATEWAY_MODE == "wecom":
        import os as _os
        missing = []
        if not _os.environ.get("WECOM_CORP_ID"): missing.append("WECOM_CORP_ID")
        if not _os.environ.get("WECOM_SECRET"): missing.append("WECOM_SECRET")
        if not _os.environ.get("WECOM_TOKEN"): missing.append("WECOM_TOKEN(回调验证)")
        if not _os.environ.get("WECOM_AES_KEY"): missing.append("WECOM_AES_KEY(消息解密)")
        if missing:
            logger.warning(f"企业微信回调缺少: {', '.join(missing)}")
        else:
            logger.info("企业微信回调配置完整, Token已就绪")

    init_db()

    print("=" * 50)
    print("  学习监督机器人 v2.0")
    print("=" * 50)

    # ── 创建适配器 ──
    mode = "wechaty" if args.live else WECHAT_GATEWAY_MODE
    adapter = create_adapter(mode, room_name=WECHAT_GROUP_NAME)

    status = adapter.get_status()
    print(f"\n适配器: {status.get('adapter', '?')}")
    print(f"房间: {status.get('room', WECHAT_GROUP_NAME)}")
    print(f"状态: {'在线' if status.get('online') else '离线'}")

    if isinstance(adapter, MockAdapter):
        print(f"模拟消息: {status.get('pending_messages', 0)} 条待处理")

    # ── Web 模式 (含调度器) ──
    if args.web:
        import uvicorn
        app = create_web_app()
        # 生产环境启动调度器
        if WECOM_DEPLOY_MODE == "production":
            scheduler = Scheduler(on_send_message=send_reply)
            scheduler.start()
            logger.info("生产模式: 调度器已启动")
        print(f"\nWeb API: http://0.0.0.0:{args.port}")
        print(f"文档: http://0.0.0.0:{args.port}/docs")
        uvicorn.run(app, host="0.0.0.0", port=args.port)
        return

    # ── 交互添加消息 ──
    if args.add_msg:
        interactive_mock()
        return

    # ── 调度器 ──
    scheduler = Scheduler(on_send_message=send_reply)
    scheduler.start()

    print(f"\n轮询间隔: {WECHAT_POLL_INTERVAL}s")
    print("按 Ctrl+C 停止\n")

    # ── 主循环 ──
    try:
        while True:
            poll_messages()
            for _ in range(WECHAT_POLL_INTERVAL):
                time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在停止...")
    finally:
        scheduler.stop()
        adapter.stop()
        print("机器人已停止")


if __name__ == "__main__":
    main()
