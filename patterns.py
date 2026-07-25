# -*- coding: utf-8 -*-
"""
融合模式 — 从开源项目提取的最佳实践
accountability-telegram-bot: 目标管理 + 主动提醒
Zenith-Study-Planner:   AI计划生成 + 情绪感知
"""

from datetime import date
from database import get_db


# ═══════════════════════════════════════════════════════════
# 模式1: 每日目标管理 (accountability-telegram-bot)
# ═══════════════════════════════════════════════════════════

def get_today_progress(user_id: str) -> dict:
    """返回今日计划完成进度百分比"""
    today = date.today().isoformat()
    db = get_db()
    total = db.execute(
        "SELECT COUNT(*) as c FROM daily_tasks WHERE user_id=? AND date(created_at)=?",
        (user_id, today)).fetchone()["c"]
    done = db.execute(
        "SELECT COUNT(*) as c FROM daily_tasks WHERE user_id=? AND date(created_at)=? AND status='completed'",
        (user_id, today)).fetchone()["c"]
    db.close()
    pct = int(done / total * 100) if total > 0 else 0
    return {"total": total, "completed": done, "percent": pct}


def generate_progress_nudge(user_id: str, username: str) -> str:
    """生成进度提醒 — 带完成百分比"""
    p = get_today_progress(user_id)
    if p["total"] == 0:
        return f"【{username}】今天还没制定计划，来列一下今天要完成的任务吧。"
    if p["percent"] == 0:
        return f"【{username}】今天计划了{p['total']}项任务，还没开始。先从最重要的一项开始吧！"
    if p["percent"] < 50:
        return f"【{username}】已完成{p['percent']}%（{p['completed']}/{p['total']}）。进度偏慢，需要加速了。"
    if p["percent"] < 100:
        return f"【{username}】完成{p['percent']}%（{p['completed']}/{p['total']}）。还剩{p['total']-p['completed']}项，加油！"
    return f"【{username}】今天计划全部完成！{p['total']}项任务，干得漂亮。"


# ═══════════════════════════════════════════════════════════
# 模式2: 主动提醒 (accountability-telegram-bot)
# ═══════════════════════════════════════════════════════════

def get_daily_greeting(username: str) -> str:
    """每日早安问候 + 今日计划提示"""
    return f"【{username}】早上好！新的一天开始了。今天的学习计划是什么？发送'今天要完成...'来制定计划。"

def get_evening_review(username: str) -> str:
    """晚间回顾提示"""
    return f"【{username}】一天结束了。回顾一下：今天完成了哪些任务？明天计划做什么？"

def get_random_nudge(username: str) -> str:
    """随机鼓励消息"""
    import random
    nudges = [
        f"【{username}】休息一下，喝杯水，然后继续。",
        f"【{username}】每完成一项任务，离考研上岸就近一步。",
        f"【{username}】不要忘了记录你的进度，这样我才能帮你跟踪。",
        f"【{username}】遇到难题了？告诉我，一起想办法。",
    ]
    return random.choice(nudges)


# ═══════════════════════════════════════════════════════════
# 模式3: 情绪感知 (Zenith-Study-Planner)
# ═══════════════════════════════════════════════════════════

def detect_mood_issue(content: str) -> str:
    """检测负面情绪, 返回调整建议"""
    mood_map = {
        "累": "今天状态不好就适当减量。完成核心任务，剩下的明天补上。休息也是备考的一部分。",
        "困": "保证睡眠比多刷几道题更重要。今晚早点睡，明天效率更高。",
        "焦虑": "焦虑是正常的。把担心的事情写下来，逐条分析。大多数焦虑来自'想太多做太少'。",
        "压力": "压力说明你在乎。试着把大目标拆成小任务，每完成一个都会减轻压力。",
        "不想学": "每个人都会有倦怠期。试试换一门学科，或者只专注25分钟（番茄钟），看看能不能启动。",
        "状态不好": "状态起伏很正常。今天可以调整：减少题量、看视频课、整理笔记，都是有效的学习。",
        "烦": "烦的时候最适合做整理类任务：整理错题、梳理知识点框架、背诵单词。不需要深度思考。",
        "坚持不下去": "想想为什么出发。你现在已经比很多放弃的人走得远了。休息一天可以，但不要彻底停下。",
    }
    for keyword, reply in mood_map.items():
        if keyword in content:
            return reply
    return ""


# ═══════════════════════════════════════════════════════════
# 模式4: AI计划生成 (Zenith-Study-Planner)
# ═══════════════════════════════════════════════════════════

def generate_study_plan_prompt(user_context: str) -> str:
    """生成AI学习计划prompt"""
    return f"""你是一个考研辅导老师。根据学生情况，生成今日学习计划。

学生信息:
{user_context}

请输出一个具体的学习计划，包括：
1. 上午任务（2-3项）
2. 下午任务（2-3项）
3. 晚上任务（1-2项）

每项注明大概时间和完成标准。总计不超过8小时。"""


# ═══════════════════════════════════════════════════════════
# 集成到现有回调
# ═══════════════════════════════════════════════════════════

def enhance_reply(user_id: str, username: str, content: str, ai_reply: str) -> str:
    """增强回复: 融合进度+情绪+AI回答"""
    parts = [ai_reply]

    # 情绪检测
    mood = detect_mood_issue(content)
    if mood:
        parts.append(mood)

    # 进度提醒(每天最多一次)
    p = get_today_progress(user_id)
    if p["total"] > 0 and p["percent"] < 50:
        parts.append(f"今日进度: {p['completed']}/{p['total']} ({p['percent']}%)")

    return "\n\n".join(p for p in parts if p)
