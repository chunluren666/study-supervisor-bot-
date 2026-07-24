# -*- coding: utf-8 -*-
"""Runtime Statistics — 运行监控与统计"""

import json, time
from datetime import datetime, date
from pathlib import Path
from threading import Lock

STATS_FILE = Path(__file__).parent / "data" / "runtime_stats.json"
STATS_FILE.parent.mkdir(exist_ok=True)
_lock = Lock()


def _load():
    if STATS_FILE.exists():
        try:
            return json.loads(STATS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return _default()


def _default():
    today = date.today().isoformat()
    return {
        "start_time": datetime.now().isoformat(),
        "restart_count": 0,
        "daily": {
            today: {
                "wx_received": 0, "wx_processed": 0, "wx_sent": 0, "wx_failed": 0,
                "ai_checks": 0, "ai_approved": 0, "ai_rejected": 0, "ai_need_more": 0,
                "tasks_created": 0, "spot_checks": 0, "reminders_sent": 0,
            }
        },
        "health": {
            "android_online": False,
            "wechat_online": False,
            "ai_online": False,
            "last_health_check": None,
        },
    }


def _save(data):
    with _lock:
        STATS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── 消息统计 ──

def msg_received():
    _inc("wx_received")

def msg_processed():
    _inc("wx_processed")

def msg_sent():
    _inc("wx_sent")

def msg_failed():
    _inc("wx_failed")

# ── AI 统计 ──

def ai_check(result: str):
    """记录AI审核结果: approved / rejected / need_more"""
    _inc("ai_checks")
    key = {"approved": "ai_approved", "rejected": "ai_rejected", "need_more": "ai_need_more"}.get(result)
    if key:
        _inc(key)

# ── 任务统计 ──

def task_created():
    _inc("tasks_created")

def spot_check_done():
    _inc("spot_checks")

def reminder_sent():
    _inc("reminders_sent")

# ── 健康状态 ──

def health_update(android: bool = None, wechat: bool = None, ai: bool = None):
    data = _load()
    h = data["health"]
    if android is not None: h["android_online"] = android
    if wechat is not None: h["wechat_online"] = wechat
    if ai is not None: h["ai_online"] = ai
    h["last_health_check"] = datetime.now().isoformat()
    _save(data)

# ── 汇总查询 ──

def get_today_stats() -> dict:
    data = _load()
    today = date.today().isoformat()
    return data["daily"].get(today, {})

def get_summary() -> dict:
    data = _load()
    today = date.today().isoformat()
    daily = data["daily"].get(today, {})

    # Calculate totals
    total_wx = sum(d.get("wx_received", 0) for d in data["daily"].values())
    total_ai = sum(d.get("ai_checks", 0) for d in data["daily"].values())

    # Uptime
    try:
        started = datetime.fromisoformat(data["start_time"])
        uptime = str(datetime.now() - started).split(".")[0]
    except Exception:
        uptime = "?"

    return {
        "uptime": uptime,
        "restart_count": data["restart_count"],
        "start_time": data["start_time"],
        "today": daily,
        "total_wx_messages": total_wx,
        "total_ai_checks": total_ai,
        "health": data["health"],
    }


def get_weekly_report() -> dict:
    """7天统计"""
    from datetime import timedelta
    data = _load()
    result = {}
    for i in range(7):
        d = (date.today() - timedelta(days=i)).isoformat()
        result[d] = data["daily"].get(d, {})
    return result


# ── 内部 ──

def _inc(field: str):
    data = _load()
    today = date.today().isoformat()
    if today not in data["daily"]:
        data["daily"][today] = {
            "wx_received": 0, "wx_processed": 0, "wx_sent": 0, "wx_failed": 0,
            "ai_checks": 0, "ai_approved": 0, "ai_rejected": 0, "ai_need_more": 0,
            "tasks_created": 0, "spot_checks": 0, "reminders_sent": 0,
        }
    data["daily"][today][field] = data["daily"][today].get(field, 0) + 1
    _save(data)


# ── 测试 ──
if __name__ == "__main__":
    msg_sent()
    msg_sent()
    msg_received()
    ai_check("approved")
    ai_check("rejected")
    task_created()
    health_update(android=True, wechat=True, ai=True)
    print(json.dumps(get_summary(), ensure_ascii=False, indent=2))
