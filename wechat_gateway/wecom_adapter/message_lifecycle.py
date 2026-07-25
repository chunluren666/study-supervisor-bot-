# -*- coding: utf-8 -*-
"""消息生命周期管理 — 幂等处理 + 状态追踪"""

import time, hashlib, logging
from datetime import datetime
from database import get_db

log = logging.getLogger("msg_lifecycle")

STATUS_RECEIVED = "received"
STATUS_PROCESSING = "processing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


def try_claim_message(msg_id: str, user_id: str, content: str) -> bool:
    """
    尝试声明消息处理权。
    如果此消息已被处理或正在处理，返回False。
    否则插入并返回True。
    """
    if not msg_id:
        msg_id = _fallback_id(user_id, content)

    db = get_db()
    try:
        existing = db.execute(
            "SELECT id, status FROM wecom_message_log WHERE msg_id=?",
            (msg_id,)
        ).fetchone()

        if existing:
            if existing["status"] in (STATUS_PROCESSING, STATUS_COMPLETED):
                db.close()
                log.debug(f"Duplicate: {msg_id} status={existing['status']}")
                return False
            # 之前失败了, 重试
            db.execute("UPDATE wecom_message_log SET status=?, content=? WHERE msg_id=?",
                       (STATUS_PROCESSING, content, msg_id))
        else:
            db.execute(
                "INSERT INTO wecom_message_log (msg_id, user_id, content, status, timestamp) "
                "VALUES (?, ?, ?, ?, ?)",
                (msg_id, user_id, content, STATUS_PROCESSING, datetime.now().isoformat())
            )
        db.commit()
        db.close()
        return True
    except Exception as e:
        log.error(f"Claim error (allowing): {e}")
        try: db.close()
        except: pass
        return True  # 异常时放行, 宁可重复不能丢消息。首次运行表不存在也会放行


def mark_completed(msg_id: str, user_id: str, content: str, reply: str):
    """标记消息处理完成"""
    if not msg_id:
        msg_id = _fallback_id(user_id, content)
    db = get_db()
    try:
        db.execute(
            "UPDATE wecom_message_log SET status=?, reply=? WHERE msg_id=? AND status=?",
            (STATUS_COMPLETED, reply, msg_id, STATUS_PROCESSING)
        )
        db.commit()
    except Exception as e:
        log.error(f"Mark completed error: {e}")
    finally:
        db.close()


def mark_failed(msg_id: str, user_id: str, content: str, error: str):
    if not msg_id:
        msg_id = _fallback_id(user_id, content)
    db = get_db()
    try:
        db.execute(
            "UPDATE wecom_message_log SET status=?, reply=? WHERE msg_id=?",
            (STATUS_FAILED, error[:200], msg_id)
        )
        db.commit()
    except Exception as e2:
        pass
    finally:
        db.close()


def is_reply_duplicate(user_id: str, reply: str, window_seconds: int = 300) -> bool:
    """检查最近N秒内是否发送过相同回复"""
    reply_hash = hashlib.md5(reply.encode()).hexdigest()
    db = get_db()
    try:
        cutoff = datetime.now().isoformat()
        row = db.execute(
            "SELECT id FROM wecom_message_log WHERE user_id=? AND reply_hash=? "
            "AND completed_at > datetime('now', ?)",
            (user_id, reply_hash, f'-{window_seconds} seconds')
        ).fetchone()
        db.close()
        return row is not None
    except Exception:
        try: db.close()
        except: pass
        return False


def save_reply_hash(msg_id: str, reply: str):
    """保存回复hash用于去重"""
    if not msg_id:
        return
    reply_hash = hashlib.md5(reply.encode()).hexdigest()
    db = get_db()
    try:
        db.execute(
            "UPDATE wecom_message_log SET reply_hash=?, completed_at=? WHERE msg_id=?",
            (reply_hash, datetime.now().isoformat(), msg_id)
        )
        db.commit()
    except Exception:
        pass
    finally:
        db.close()


def _fallback_id(user_id: str, content: str) -> str:
    h = hashlib.md5(f"{user_id}:{content}:{int(time.time()//10)}".encode()).hexdigest()
    return f"fb_{h[:16]}"
