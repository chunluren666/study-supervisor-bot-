# -*- coding: utf-8 -*-
"""AI 模块 — 专业考研辅导老师"""

import json, time, urllib.request, urllib.error
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


def _call_deepseek(system_prompt: str, user_message: str,
                   temperature: float = 0.7) -> str:
    """调用DeepSeek，1次重试。用于问答场景temperature偏高，监督场景偏低"""
    if not DEEPSEEK_API_KEY:
        return ""
    for attempt in range(2):
        try:
            body = json.dumps({
                "model": DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "temperature": temperature, "max_tokens": 600,
            }).encode("utf-8")
            req = urllib.request.Request(f"{DEEPSEEK_BASE_URL}/chat/completions", data=body,
                headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                         "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=25) as resp:
                return json.loads(resp.read().decode("utf-8"))["choices"][0]["message"]["content"].strip()
        except Exception:
            if attempt == 0: time.sleep(1)
    return ""


# ── 考研老师系统提示词 ──

TEACHER_SYSTEM = """# 身份
你是一名大学四年级考研辅导老师。你的学生都是正在准备研究生考试的大四本科生。

# 默认学生画像
- 年级：大四
- 状态：正在备考考研
- 面临：初试复习、择校、专业选择、时间规划、心理压力

# 你的目标
帮助学生提高考研成功率。

# 你的职责
1. 考研规划：全年/月/周/日复习计划，各阶段安排
2. 公共课：数学一二三、英语一二、政治的学习方法、题目讲解
3. 专业课：复习方法、真题分析、知识点规划
4. 择校择专业：院校选择、分数线、竞争分析
5. 学习监督：任务跟踪、完成审核、效率分析
6. 考研心理：压力、焦虑、坚持问题的疏导

# 回答风格
- 像真实老师在和学生交流，不要像客服机器人
- 不要给空洞建议如"多练习"——要追问具体情况后给针对性方案
- 信息不足时先问清楚学生的阶段/科目/基础再回答
- 回答简洁（150字以内），直接有用

# 非考研问题
如果学生问与考研完全无关的内容（如游戏、娱乐、天气），回复：
"我是你的考研辅导老师，主要帮你解决考研备考、学习规划和复习中的问题。如果是考研相关问题，可以直接告诉我。"
不要展开回答非考研内容。

# 学生信息
{user_context}

# 近期对话
{chat_history}

请用中文回答。"""


def answer_question(question: str, user_context: str = "", chat_history: str = "") -> str:
    """回答考研问题"""
    prompt = TEACHER_SYSTEM.format(user_context=user_context or "新学生，暂无信息",
                                    chat_history=chat_history or "无")
    return _call_deepseek(prompt, question, temperature=0.7)


# ── 意图分类 ──

INTENT_PROMPT = """判断学生消息意图，只返回一个词：

- "task" — 学习汇报（含具体数字+科目+内容描述，如"完成数学30道""背了100个单词"）
- "question" — 考研相关问题（怎么复习/如何规划/用什么书/院校选择/心态调整）
- "chat" — 闲聊天/打招呼/非学习内容

消息: {message}

只返回一个词。"""


def classify_intent(message: str) -> str:
    result = _call_deepseek(INTENT_PROMPT.format(message=message), "", temperature=0.1)
    result = result.strip().lower()
    if "task" in result: return "task"
    if "question" in result: return "question"
    return "chat"


# ── 完成审核 ──

COMPLETE_CHECK_PROMPT = """学生提交了学习汇报。作为考研老师，你必须核实这五项：

1. 科目
2. 内容（哪本书/哪套题/哪个章节）
3. 数量
4. 时间
5. 结果（正确率/掌握程度）

缺3项以上→rejected:追问缺失项
只说"做完了/好了"→rejected
有具体数字→approved 或 need_more

任务: {task_content}
汇报: {user_message}

JSON: {"decision":"approved|need_more|rejected","reason":"像老师说话的语气","quality":"good|ok|poor"}
只返回JSON。"""


def check_completion(task_content: str, user_message: str) -> dict:
    prompt = COMPLETE_CHECK_PROMPT.format(task_content=task_content, user_message=user_message)
    result = _call_deepseek(prompt, "", temperature=0.3)
    try:
        if "```" in result: result = result.split("```")[1].replace("json", "", 1)
        return json.loads(result.strip())
    except json.JSONDecodeError:
        if len(user_message) > 50:
            return {"decision": "need_more", "reason": "请补充具体数字和结果"}
        return {"decision": "rejected", "reason": "这不是合格的学习汇报。请说明科目/内容/数量/时间/结果"}


# ── 保留兼容接口 ──

def parse_task_message(message: str) -> dict:
    """保留原有接口"""
    return {"intent": "unknown"}

def evaluate_spot_check(question: str, answer: str) -> dict:
    return {"status": "normal", "comment": "已记录", "suggestion": ""}

def generate_study_advice(report, c, t, s):
    return ""
