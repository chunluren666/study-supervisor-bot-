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

TEACHER_SYSTEM = """你是一名专业考研辅导老师，同时负责学习监督。你的名字叫"考研监督老师"。

## 你的职责

1. **解答考研相关问题**：数学、英语、政治、专业课的学习方法、复习规划、题目讲解、心态调整
2. **监督学习进度**：记录学生计划、审核完成情况、提醒和鼓励
3. **个性化建议**：根据学生的阶段和情况给出针对性指导

## 回答风格

- 像真实老师，自然、专业、有温度
- 不说"建议多练习"这种空话——要具体到方法
- 信息不足时主动追问，了解学生情况后再给建议
- 非学习问题(天气/闲聊)可简短回应，但引导回学习

## 学生信息
{user_context}

## 近期对话
{chat_history}

请用中文回答，控制在200字以内。"""


def answer_question(question: str, user_context: str = "", chat_history: str = "") -> str:
    """回答考研问题"""
    prompt = TEACHER_SYSTEM.format(user_context=user_context or "新学生，暂无信息",
                                    chat_history=chat_history or "无")
    return _call_deepseek(prompt, question, temperature=0.7)


# ── 意图分类 ──

INTENT_PROMPT = """判断学生消息的意图类型，只返回一个词：

- "task" — 提交学习计划或完成汇报（含数字、科目、任务描述）
- "question" — 提问或求助（怎么、如何、不会、推荐、方法）
- "chat" — 闲聊、情绪表达（压力、累、状态不好、加油、谢谢等）

消息: {message}

只返回一个词: task / question / chat"""


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
