# -*- coding: utf-8 -*-
"""
数据库层——SQLite 建表 + 基本 CRUD
"""

import sqlite3
import json
import time
from datetime import datetime
from pathlib import Path
from config import DATABASE_PATH, BASE_DIR


def get_db():
    """获取数据库连接（启用 WAL 模式提升并发性能）"""
    for retry in range(3):
        try:
            conn = sqlite3.connect(str(DATABASE_PATH), timeout=10)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=5000")
            return conn
        except sqlite3.OperationalError:
            if retry < 2:
                time.sleep(1)
            else:
                raise


# ── 数据库备份 ──

def backup_database():
    """备份数据库到 backups/ 目录"""
    import shutil
    backup_dir = BASE_DIR / "backups"
    backup_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"supervisor_{ts}.db"
    try:
        shutil.copy2(str(DATABASE_PATH), str(backup_path))
        # 只保留最近 7 天的备份
        all_backups = sorted(backup_dir.glob("supervisor_*.db"))
        for old in all_backups[:-7]:
            old.unlink()
        return str(backup_path)
    except Exception as e:
        print(f"[DB] Backup failed: {e}")
        return None


def init_db():
    """首次运行时创建所有表"""
    db = get_db()
    db.executescript("""
        -- 成员表
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wx_name TEXT UNIQUE NOT NULL,      -- 微信昵称
            display_name TEXT,                 -- 显示名
            role TEXT DEFAULT 'member',        -- member / admin
            join_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 任务表
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,               -- 任务标题
            content TEXT,                      -- 详细内容
            deadline TIMESTAMP,                -- 截止时间
            publisher_id INTEGER,              -- 发布者(关联members)
            status TEXT DEFAULT '未开始',
            raw_message TEXT,                  -- 原始消息
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (publisher_id) REFERENCES members(id)
        );

        -- 任务分配表（多对多：一个任务可分配给多人）
        -- 状态流转: pending → submitted → reviewing → approved → rejected
        CREATE TABLE IF NOT EXISTS task_assignees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            member_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            completed_at TIMESTAMP,
            answer TEXT,
            ai_result TEXT,
            ai_audit_reason TEXT,              -- AI审核理由
            FOREIGN KEY (task_id) REFERENCES tasks(id),
            FOREIGN KEY (member_id) REFERENCES members(id),
            UNIQUE(task_id, member_id)
        );

        -- 完成证据表
        CREATE TABLE IF NOT EXISTS completion_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignee_id INTEGER NOT NULL,
            evidence_type TEXT DEFAULT 'text',  -- text / image / file / summary
            text_content TEXT,                   -- 文字说明
            file_path TEXT,                      -- 文件路径
            image_path TEXT,                     -- 图片路径
            ai_audit_result TEXT,                -- AI审核结果
            ai_audit_reason TEXT,                -- AI审核理由
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (assignee_id) REFERENCES task_assignees(id)
        );

        -- 风险分析表
        CREATE TABLE IF NOT EXISTS risk_assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            risk_level TEXT DEFAULT 'low',     -- low / medium / high
            risk_score REAL DEFAULT 0.0,       -- 风险分 0-100
            completion_rate REAL DEFAULT 0.0,
            overdue_count INTEGER DEFAULT 0,
            score_trend TEXT,                  -- up / stable / down
            streak_fails INTEGER DEFAULT 0,    -- 连续未完成次数
            detail_json TEXT,                  -- 详细分析JSON
            assessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (member_id) REFERENCES members(id)
        );

        -- 周报/月报表
        CREATE TABLE IF NOT EXISTS weekly_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_type TEXT NOT NULL,         -- weekly / monthly
            member_id INTEGER,                 -- NULL=群报告
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (member_id) REFERENCES members(id)
        );

        -- 学习评分表
        CREATE TABLE IF NOT EXISTS study_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            completion_rate REAL DEFAULT 0.0,   -- 完成率 0-100
            timeliness_rate REAL DEFAULT 0.0,   -- 及时率 0-100
            quality_score REAL DEFAULT 0.0,     -- 质量评分 0-100
            overall_score REAL DEFAULT 0.0,     -- 综合评分 0-100
            streak_days INTEGER DEFAULT 0,      -- 连续学习天数
            comment TEXT,                        -- AI评价
            calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (member_id) REFERENCES members(id)
        );

        -- 抽查记录
        CREATE TABLE IF NOT EXISTS spot_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            question TEXT NOT NULL,            -- 抽查问题
            answer TEXT,                       -- 成员回复
            ai_judgment TEXT,                  -- AI评价
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            answered_at TIMESTAMP,
            FOREIGN KEY (member_id) REFERENCES members(id)
        );

        -- 提醒记录
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            member_id INTEGER,
            remind_type TEXT NOT NULL,         -- deadline_warning / overdue / spot_check
            message TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks(id),
            FOREIGN KEY (member_id) REFERENCES members(id)
        );

        -- 每日计划
        CREATE TABLE IF NOT EXISTS daily_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            date TEXT NOT NULL,
            raw_message TEXT,
            total_hours REAL DEFAULT 0,
            morning_review_at TIMESTAMP,
            afternoon_remind_at TIMESTAMP,
            evening_check_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 每日任务明细
        CREATE TABLE IF NOT EXISTS daily_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            user_id TEXT NOT NULL,
            subject TEXT,
            content TEXT,
            target_count TEXT,
            estimated_minutes INTEGER DEFAULT 0,
            priority TEXT DEFAULT 'medium',
            status TEXT DEFAULT 'pending',
            actual_count TEXT,
            actual_minutes INTEGER DEFAULT 0,
            note TEXT,
            completed_at TIMESTAMP,
            FOREIGN KEY (plan_id) REFERENCES daily_plans(id)
        );

        -- 用户画像
        CREATE TABLE IF NOT EXISTS user_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wecom_userid TEXT UNIQUE NOT NULL,
            username TEXT DEFAULT '',
            target_school TEXT DEFAULT '',
            major TEXT DEFAULT '',
            exam_subjects TEXT DEFAULT '',
            study_stage TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 聊天历史
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            userid TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Worker消息队列
        CREATE TABLE IF NOT EXISTS worker_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            content TEXT NOT NULL,
            msg_id TEXT,
            chat_id TEXT,
            status TEXT DEFAULT 'pending',
            reply TEXT,
            retry_count INTEGER DEFAULT 0,
            elapsed_ms INTEGER DEFAULT 0,
            last_error TEXT,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 企业微信消息日志（去重 + 生命周期）
        CREATE TABLE IF NOT EXISTS wecom_message_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            msg_id TEXT UNIQUE NOT NULL,
            user_id TEXT,
            content TEXT,
            raw_xml TEXT,
            timestamp TEXT,
            status TEXT DEFAULT 'received',
            reply TEXT,
            reply_hash TEXT,
            completed_at TIMESTAMP,
            processed BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 消息日志（用于去重）
        CREATE TABLE IF NOT EXISTS message_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_hash TEXT UNIQUE NOT NULL,
            sender TEXT,
            raw_content TEXT,
            processed BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    db.commit()
    db.close()


# ── 成员管理 ──

# ── 角色常量 ──
ROLE_STUDENT = "student"
ROLE_TEACHER = "teacher"
ROLE_ADMIN = "admin"

VALID_ROLES = (ROLE_STUDENT, ROLE_TEACHER, ROLE_ADMIN)


def ensure_member(wx_name: str, role: str = ROLE_STUDENT, db=None) -> int:
    """获取或创建成员，返回 member_id。已存在时更新角色"""
    own_db = db is None
    if own_db:
        db = get_db()
    row = db.execute("SELECT id, role FROM members WHERE wx_name = ?", (wx_name,)).fetchone()
    if row:
        # 如果角色不同则更新
        if row["role"] != role:
            db.execute("UPDATE members SET role = ? WHERE id = ?", (role, row["id"]))
            db.commit()
        if own_db:
            db.close()
        return row["id"]
    db.execute("INSERT INTO members (wx_name, display_name, role) VALUES (?, ?, ?)",
               (wx_name, wx_name, role))
    db.commit()
    mid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    if own_db:
        db.close()
    return mid


def list_members():
    """列出所有成员"""
    db = get_db()
    rows = db.execute("SELECT * FROM members ORDER BY id").fetchall()
    db.close()
    return [dict(r) for r in rows]


# ── 任务管理 ──

def create_task(title: str, content: str, deadline: str = None,
                publisher_name: str = "", assignee_names: list = None) -> int:
    """创建任务，自动关联发布者和分配成员"""
    db = get_db()
    pub_id = ensure_member(publisher_name, db=db) if publisher_name else None

    db.execute(
        "INSERT INTO tasks (title, content, deadline, publisher_id, raw_message) VALUES (?, ?, ?, ?, ?)",
        (title, content, deadline, pub_id, "")
    )
    task_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    # 分配成员
    if assignee_names:
        for name in assignee_names:
            mid = ensure_member(name, db=db)
            db.execute(
                "INSERT OR IGNORE INTO task_assignees (task_id, member_id) VALUES (?, ?)",
                (task_id, mid)
            )

    db.commit()
    db.close()
    return task_id


def get_pending_tasks():
    """获取所有未完成任务"""
    db = get_db()
    rows = db.execute(
        """SELECT t.*, m.wx_name as publisher_name
           FROM tasks t
           LEFT JOIN members m ON t.publisher_id = m.id
           WHERE t.status IN ('未开始', '进行中')
           ORDER BY t.deadline ASC"""
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def get_tasks_by_member(member_name: str):
    """获取某个成员的未完成任务"""
    db = get_db()
    rows = db.execute(
        """SELECT t.*, ta.status as assignee_status, ta.answer, ta.ai_result
           FROM tasks t
           JOIN task_assignees ta ON t.id = ta.task_id
           JOIN members m ON ta.member_id = m.id
           WHERE m.wx_name = ? AND t.status != '已完成'
           ORDER BY t.deadline ASC""",
        (member_name,)
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def update_task_status(task_id: int, status: str):
    """更新任务状态"""
    db = get_db()
    db.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
    db.commit()
    db.close()


def complete_task(task_id: int, member_name: str, answer: str = "",
                  ai_result: str = ""):
    """成员完成任务"""
    db = get_db()
    mid = ensure_member(member_name)
    db.execute(
        """UPDATE task_assignees
           SET status = '已完成', completed_at = ?, answer = ?, ai_result = ?
           WHERE task_id = ? AND member_id = ?""",
        (datetime.now().isoformat(), answer, ai_result, task_id, mid)
    )
    # 如果所有人都完成了，更新主任务状态
    remaining = db.execute(
        "SELECT COUNT(*) as c FROM task_assignees WHERE task_id = ? AND status != '已完成'",
        (task_id,)
    ).fetchone()
    if remaining["c"] == 0:
        db.execute("UPDATE tasks SET status = '已完成' WHERE id = ?", (task_id,))
    db.commit()
    db.close()


# ── 抽查 ──

def create_spot_check(member_id: int, question: str) -> int:
    db = get_db()
    db.execute(
        "INSERT INTO spot_checks (member_id, question) VALUES (?, ?)",
        (member_id, question)
    )
    sid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.commit()
    db.close()
    return sid


def answer_spot_check(check_id: int, answer: str, ai_judgment: str = ""):
    db = get_db()
    db.execute(
        "UPDATE spot_checks SET answer = ?, ai_judgment = ?, answered_at = ? WHERE id = ?",
        (answer, ai_judgment, datetime.now().isoformat(), check_id)
    )
    db.commit()
    db.close()


# ── 提醒 ──

def add_reminder(task_id: int, member_id: int, remind_type: str, message: str):
    db = get_db()
    db.execute(
        "INSERT INTO reminders (task_id, member_id, remind_type, message) VALUES (?, ?, ?, ?)",
        (task_id, member_id, remind_type, message)
    )
    db.commit()
    db.close()


# ── 消息去重 ──

def is_duplicate_message(content_hash: str) -> bool:
    db = get_db()
    row = db.execute(
        "SELECT id FROM message_log WHERE content_hash = ?", (content_hash,)
    ).fetchone()
    db.close()
    return row is not None


def log_message(content_hash: str, sender: str, raw: str):
    db = get_db()
    db.execute(
        "INSERT OR IGNORE INTO message_log (content_hash, sender, raw_content) VALUES (?, ?, ?)",
        (content_hash, sender, raw)
    )
    db.commit()
    db.close()


# ── 统计 ──

def get_member_stats(member_name: str):
    """获取单个成员统计"""
    db = get_db()
    mid = ensure_member(member_name)
    total = db.execute(
        "SELECT COUNT(*) as c FROM task_assignees WHERE member_id = ?", (mid,)
    ).fetchone()["c"]
    completed = db.execute(
        "SELECT COUNT(*) as c FROM task_assignees WHERE member_id = ? AND status = '已完成'", (mid,)
    ).fetchone()["c"]
    overdue = db.execute(
        "SELECT COUNT(*) as c FROM task_assignees ta JOIN tasks t ON ta.task_id = t.id "
        "WHERE ta.member_id = ? AND t.status = '已逾期'", (mid,)
    ).fetchone()["c"]
    # Recent spot checks
    recent = db.execute(
        "SELECT * FROM spot_checks WHERE member_id = ? ORDER BY created_at DESC LIMIT 3",
        (mid,)
    ).fetchall()
    db.close()
    return {
        "total": total,
        "completed": completed,
        "overdue": overdue,
        "recent_checks": [dict(r) for r in recent]
    }


def get_all_stats():
    """获取所有成员统计"""
    members = list_members()
    stats = []
    for m in members:
        s = get_member_stats(m["wx_name"])
        s["name"] = m["wx_name"]
        stats.append(s)
    return stats


# ── 完成证据 ──

# 状态常量
STATUS_PENDING = "pending"
STATUS_SUBMITTED = "submitted"
STATUS_REVIEWING = "reviewing"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"


def submit_evidence(assignee_id: int, evidence_type: str = "text",
                    text_content: str = "", file_path: str = "",
                    image_path: str = "") -> int:
    """提交完成证据"""
    db = get_db()
    # 更新任务分配状态
    db.execute(
        "UPDATE task_assignees SET status = ?, answer = ? WHERE id = ?",
        (STATUS_SUBMITTED, text_content, assignee_id)
    )
    # 插入证据
    db.execute(
        "INSERT INTO completion_evidence (assignee_id, evidence_type, text_content, file_path, image_path) "
        "VALUES (?, ?, ?, ?, ?)",
        (assignee_id, evidence_type, text_content, file_path, image_path)
    )
    eid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.commit()
    db.close()
    return eid


def audit_evidence(assignee_id: int, evidence_id: int, decision: str,
                   reason: str = ""):
    """审核证据，更新任务状态"""
    db = get_db()
    status = STATUS_APPROVED if decision == "approved" else STATUS_REJECTED
    if decision == "need_more":
        status = STATUS_REJECTED
    db.execute(
        "UPDATE task_assignees SET status = ?, ai_audit_reason = ? WHERE id = ?",
        (status, reason, assignee_id)
    )
    db.execute(
        "UPDATE completion_evidence SET ai_audit_result = ?, ai_audit_reason = ? WHERE id = ?",
        (decision, reason, evidence_id)
    )
    if status == STATUS_APPROVED:
        db.execute(
            "UPDATE task_assignees SET completed_at = ? WHERE id = ?",
            (datetime.now().isoformat(), assignee_id)
        )
        # 检查任务是否全部完成
        task_row = db.execute(
            "SELECT task_id FROM task_assignees WHERE id = ?", (assignee_id,)
        ).fetchone()
        if task_row:
            remaining = db.execute(
                "SELECT COUNT(*) as c FROM task_assignees "
                "WHERE task_id = ? AND status != ?",
                (task_row["task_id"], STATUS_APPROVED)
            ).fetchone()
            if remaining["c"] == 0:
                db.execute("UPDATE tasks SET status = '已完成' WHERE id = ?",
                          (task_row["task_id"],))
    db.commit()
    db.close()


def get_evidence(assignee_id: int) -> list:
    """获取某次任务分配的所有证据"""
    db = get_db()
    rows = db.execute(
        "SELECT * FROM completion_evidence WHERE assignee_id = ? ORDER BY submitted_at DESC",
        (assignee_id,)
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


# ── 学习评分 ──

def save_score(member_id: int, completion_rate: float, timeliness_rate: float,
               quality_score: float, overall_score: float, streak_days: int,
               comment: str = "") -> int:
    """保存评分"""
    db = get_db()
    db.execute(
        "INSERT INTO study_scores (member_id, completion_rate, timeliness_rate, "
        "quality_score, overall_score, streak_days, comment) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (member_id, completion_rate, timeliness_rate, quality_score,
         overall_score, streak_days, comment)
    )
    sid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.commit()
    db.close()
    return sid


def get_latest_score(member_id: int) -> dict:
    """获取最新评分"""
    db = get_db()
    row = db.execute(
        "SELECT * FROM study_scores WHERE member_id = ? ORDER BY calculated_at DESC LIMIT 1",
        (member_id,)
    ).fetchone()
    db.close()
    return dict(row) if row else {}


def get_score_history(member_id: int, limit: int = 10) -> list:
    """获取评分历史"""
    db = get_db()
    rows = db.execute(
        "SELECT * FROM study_scores WHERE member_id = ? ORDER BY calculated_at DESC LIMIT ?",
        (member_id, limit)
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def get_assignee_by_task_and_member(task_id: int, member_name: str) -> dict:
    """根据任务ID和成员名获取分配记录"""
    db = get_db()
    row = db.execute(
        "SELECT ta.* FROM task_assignees ta JOIN members m ON ta.member_id = m.id "
        "WHERE ta.task_id = ? AND m.wx_name = ?",
        (task_id, member_name)
    ).fetchone()
    db.close()
    return dict(row) if row else {}


# ── 风险分析 ──

def save_risk_assessment(member_id: int, risk_level: str, risk_score: float,
                         completion_rate: float, overdue_count: int,
                         score_trend: str, streak_fails: int,
                         detail_json: str = "") -> int:
    """保存风险评估"""
    db = get_db()
    db.execute(
        "INSERT INTO risk_assessments (member_id, risk_level, risk_score, "
        "completion_rate, overdue_count, score_trend, streak_fails, detail_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (member_id, risk_level, risk_score, completion_rate,
         overdue_count, score_trend, streak_fails, detail_json)
    )
    rid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.commit()
    db.close()
    return rid


def get_latest_risk(member_id: int) -> dict:
    """获取最新风险评估"""
    db = get_db()
    row = db.execute(
        "SELECT * FROM risk_assessments WHERE member_id = ? "
        "ORDER BY assessed_at DESC LIMIT 1", (member_id,)
    ).fetchone()
    db.close()
    return dict(row) if row else {}


def get_all_risks() -> list:
    """获取所有成员最新风险"""
    db = get_db()
    rows = db.execute(
        "SELECT r.*, m.wx_name FROM risk_assessments r "
        "JOIN members m ON r.member_id = m.id "
        "WHERE r.id IN (SELECT MAX(id) FROM risk_assessments GROUP BY member_id)"
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def get_overdue_count(member_id: int) -> int:
    """获取成员逾期次数"""
    db = get_db()
    row = db.execute(
        "SELECT COUNT(*) as c FROM task_assignees ta "
        "JOIN tasks t ON ta.task_id = t.id "
        "WHERE ta.member_id = ? AND t.status = '已逾期'", (member_id,)
    ).fetchone()
    db.close()
    return row["c"] if row else 0


def get_streak_fails(member_id: int) -> int:
    """获取连续未完成次数（rejected/overdue）"""
    db = get_db()
    rows = db.execute(
        "SELECT ta.status FROM task_assignees ta "
        "WHERE ta.member_id = ? AND ta.status IN ('rejected', 'submitted') "
        "ORDER BY ta.id DESC LIMIT 10", (member_id,)
    ).fetchall()
    db.close()
    streak = 0
    for r in rows:
        if r["status"] in ("rejected", "submitted"):
            streak += 1
        else:
            break
    return streak


# ── 周报/月报 ──

def save_report(report_type: str, title: str, content: str,
                member_id: int = None) -> int:
    """保存报告"""
    db = get_db()
    db.execute(
        "INSERT INTO weekly_reports (report_type, member_id, title, content) "
        "VALUES (?, ?, ?, ?)", (report_type, member_id, title, content)
    )
    rid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.commit()
    db.close()
    return rid


def get_reports(report_type: str = None, limit: int = 10) -> list:
    """获取报告列表"""
    db = get_db()
    if report_type:
        rows = db.execute(
            "SELECT * FROM weekly_reports WHERE report_type = ? "
            "ORDER BY generated_at DESC LIMIT ?", (report_type, limit)
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM weekly_reports ORDER BY generated_at DESC LIMIT ?", (limit,)
        ).fetchall()
    db.close()
    return [dict(r) for r in rows]


# ── 角色/权限 ──

def get_member_role(wx_name: str) -> str:
    """获取成员角色"""
    db = get_db()
    row = db.execute("SELECT role FROM members WHERE wx_name = ?", (wx_name,)).fetchone()
    db.close()
    return row["role"] if row else ROLE_STUDENT


def set_member_role(wx_name: str, role: str):
    """设置成员角色"""
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role: {role}. Choose: {VALID_ROLES}")
    mid = ensure_member(wx_name, role=role)
    db = get_db()
    db.execute("UPDATE members SET role = ? WHERE id = ?", (role, mid))
    db.commit()
    db.close()


def is_teacher_or_admin(wx_name: str) -> bool:
    return get_member_role(wx_name) in (ROLE_TEACHER, ROLE_ADMIN)


def is_admin(wx_name: str) -> bool:
    return get_member_role(wx_name) == ROLE_ADMIN


def can_publish_task(wx_name: str) -> bool:
    """只有 teacher/admin 可以发布任务"""
    return is_teacher_or_admin(wx_name)


def can_view_all_stats(wx_name: str) -> bool:
    return is_teacher_or_admin(wx_name)


def can_modify_task(wx_name: str) -> bool:
    return is_admin(wx_name)


# ── 企业微信消息去重 ──

def is_wecom_duplicate(msg_id: str) -> bool:
    db = get_db()
    row = db.execute("SELECT id FROM wecom_message_log WHERE msg_id = ?", (msg_id,)).fetchone()
    db.close()
    return row is not None

def log_wecom_message(msg_id: str, user_id: str, content: str, raw_xml: str = "",
                      timestamp: str = ""):
    db = get_db()
    db.execute(
        "INSERT OR IGNORE INTO wecom_message_log (msg_id, user_id, content, raw_xml, timestamp) "
        "VALUES (?, ?, ?, ?, ?)", (msg_id, user_id, content, raw_xml, timestamp)
    )
    db.commit()
    db.close()


# ── 初始化 ──
if __name__ == "__main__":
    init_db()
    print("数据库初始化完成:", DATABASE_PATH)
