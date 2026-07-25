# -*- coding: utf-8 -*-
"""
消息队列 Worker — 异步处理 AI + 发送回复
callback → save queue → return OK
worker   → pickup → AI → send → update status
"""

import json, time, threading, logging
from datetime import datetime
from pathlib import Path
from database import get_db

LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

log = logging.getLogger("wecom_worker")
log.setLevel(logging.INFO)

STATUS_PENDING = "pending"
STATUS_PROCESSING = "processing"
STATUS_DONE = "done"
STATUS_FAILED = "failed"


# ── 队列操作 ──

def enqueue_message(sender: str, content: str, msg_id: str = "", chat_id: str = ""):
    """消息入队(在callback中调用)"""
    db = get_db()
    db.execute(
        "INSERT INTO worker_queue (sender, content, msg_id, chat_id, status) VALUES (?, ?, ?, ?, ?)",
        (sender, content, msg_id, chat_id, STATUS_PENDING)
    )
    db.commit()
    db.close()
    log.debug(f"入队: [{sender}] {content[:50]}")


def get_next_pending() -> dict:
    """取一条待处理消息并标记为processing"""
    db = get_db()
    row = db.execute(
        "SELECT * FROM worker_queue WHERE status=? ORDER BY id ASC LIMIT 1",
        (STATUS_PENDING,)
    ).fetchone()
    if not row:
        db.close()
        return {}
    db.execute("UPDATE worker_queue SET status=?, started_at=? WHERE id=?",
               (STATUS_PROCESSING, datetime.now().isoformat(), row["id"]))
    db.commit()
    db.close()
    return dict(row)


def mark_done(queue_id: int, reply: str, elapsed_ms: int):
    db = get_db()
    db.execute(
        "UPDATE worker_queue SET status=?, reply=?, elapsed_ms=?, completed_at=? WHERE id=?",
        (STATUS_DONE, reply, elapsed_ms, datetime.now().isoformat(), queue_id)
    )
    db.commit()
    db.close()


def mark_failed(queue_id: int, error: str, retry: int):
    db = get_db()
    status = STATUS_PENDING if retry < 3 else STATUS_FAILED
    db.execute(
        "UPDATE worker_queue SET status=?, retry_count=?, last_error=? WHERE id=?",
        (status, retry, error, queue_id)
    )
    db.commit()
    db.close()


def cleanup_old(days: int = 7):
    db = get_db()
    db.execute("DELETE FROM worker_queue WHERE status IN ('done','failed') AND datetime(completed_at) < datetime('now', ?)",
               (f'-{days} days',))
    db.commit()
    db.close()


# ── Worker ──

class MessageWorker:
    """后台消息处理器"""

    def __init__(self, process_fn, send_fn):
        self.process = process_fn  # task_manager.process_message
        self.send = send_fn        # adapter.send_message
        self.running = False
        self.stats = {"processed": 0, "failed": 0, "avg_ms": 0}

    def start(self):
        self.running = True
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()
        log.info("Worker started")

    def stop(self):
        self.running = False

    def _loop(self):
        while self.running:
            try:
                msg = get_next_pending()
                if not msg:
                    time.sleep(0.5)
                    continue

                queue_id = msg["id"]
                sender = msg["sender"]
                content = msg["content"]
                t0 = time.time()

                try:
                    reply = self.process(sender, content) or ""
                    if reply and self.send:
                        self.send(reply)
                    elapsed = int((time.time() - t0) * 1000)
                    mark_done(queue_id, reply, elapsed)
                    self.stats["processed"] += 1
                    self.stats["avg_ms"] = (self.stats["avg_ms"] * (self.stats["processed"] - 1) + elapsed) // self.stats["processed"]
                    log.info(f"Done [{sender}] {elapsed}ms")
                except Exception as e:
                    retry = msg.get("retry_count", 0) + 1
                    mark_failed(queue_id, str(e)[:200], retry)
                    self.stats["failed"] += 1
                    log.error(f"Failed [{sender}] retry={retry}: {e}")

            except Exception as e:
                log.error(f"Worker loop: {e}")
                time.sleep(1)
