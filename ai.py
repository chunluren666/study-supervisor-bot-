# -*- coding: utf-8 -*-
"""
AI 模块 — 严格考研监督老师
"""

import json, time, urllib.request, urllib.error
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


def _call_deepseek(system_prompt: str, user_message: str,
                   temperature: float = 0.3) -> str:
    if not DEEPSEEK_API_KEY:
        return _fallback_parse(user_message)

    MAX_RETRIES, RETRY_DELAY = 1, 1  # 快速失败, fallback秒回
    for attempt in range(MAX_RETRIES):
        try:
            body = json.dumps({
                "model": DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "temperature": temperature, "max_tokens": 500,
            }).encode("utf-8")
            req = urllib.request.Request(f"{DEEPSEEK_BASE_URL}/chat/completions", data=body,
                headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                         "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))["choices"][0]["message"]["content"].strip()
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
    return _fallback_parse(user_message)


# ── 回退 ──

def _fallback_parse(msg: str) -> str:
    if any(kw in msg for kw in ["任务", "今天完成", "提交", "截止", "负责"]):
        import re
        names = list(set(re.findall(r'([一-龥]{2,4})(?=负责|完成|提交|和)', msg)))
        return json.dumps({"intent": "task_publish", "title": msg[:50], "content": msg,
                           "deadline": None, "assignees": names}, ensure_ascii=False)
    if any(kw in msg for kw in ["完成了", "做完了", "好了", "搞定了", "提交了"]):
        return json.dumps({"intent": "task_complete", "task_hint": msg}, ensure_ascii=False)
    return json.dumps({"intent": "unknown"}, ensure_ascii=False)


# ── 1. 消息解析 — 严格老师 ──

TASK_PARSE_PROMPT = """你是一个**严格的考研监督老师**。分析学生发来的消息，判断类型。

如果是**老师发布任务**，提取:
{"intent":"task_publish","title":"任务标题","content":"完整内容","deadline":null,"assignees":["成员"]}

如果是**学生学习汇报**，检查是否具体(有数字/学科名/教材/章节等):
{"intent":"study_report","subjects":["学科"],"content":"摘要","specific":true/false,"completion":"完成情况"}

只返回JSON。"""


def parse_task_message(message: str) -> dict:
    result = _call_deepseek(TASK_PARSE_PROMPT, message)
    try:
        if "```" in result: result = result.split("```")[1].replace("json", "", 1)
        return json.loads(result.strip())
    except json.JSONDecodeError:
        return {"intent": "unknown"}


# ── 2. 完成审核 — 严格要求具体信息 ──

COMPLETE_CHECK_PROMPT = """你是一个**严格的考研监督老师**。学生提交了学习完成汇报，你必须严格审核。

**必需的五个要素：**
1. 学科 — 数学/英语/政治/专业课？
2. 内容 — 哪本书/哪套题/哪个章节？
3. 时间 — 花了多久？
4. 数量 — 做了多少题/看了多少页？
5. 结果 — 正确率/掌握程度/错题是否整理？

**判断标准：**
- 缺少3项以上 → rejected: "信息严重不足，请按学科/内容/时间/数量/结果说明"
- 只说"做完了/好了" → rejected: "这不是合格的学习汇报，请具体说明"
- 有3-4项但缺关键信息 → need_more: 追问缺失项
- 5项齐全且有具体数字 → approved

任务要求: {task_content}
学生提交: {user_message}

返回JSON: {"decision":"approved|need_more|rejected","reason":"简短理由","quality":"good|ok|poor","missing":["缺失项"]}
只返回JSON。"""


def check_completion(task_content: str, user_message: str) -> dict:
    prompt = COMPLETE_CHECK_PROMPT.format(task_content=task_content, user_message=user_message)
    result = _call_deepseek("你是一个严格的考研监督老师。只返回JSON。", prompt)
    try:
        if "```" in result: result = result.split("```")[1].replace("json", "", 1)
        return json.loads(result.strip())
    except json.JSONDecodeError:
        if len(user_message) > 50:
            return {"decision": "need_more", "reason": "请明确说明学科/内容/数量"}
        return {"decision": "rejected", "reason": "这不是合格的学习汇报。请说明: 1.学科 2.内容 3.数量 4.时间 5.结果"}


# ── 3. 抽查评估 ──

SPOT_CHECK_PROMPT = """你是一个严格的考研监督老师。你抽查了学生，根据回复评估状态。

抽查: {question}
学生回复: {answer}

返回JSON: {"status":"good|normal|warning","comment":"评价","suggestion":"建议"}
只返回JSON。"""


def evaluate_spot_check(question: str, answer: str) -> dict:
    prompt = SPOT_CHECK_PROMPT.format(question=question, answer=answer)
    result = _call_deepseek("严格的考研监督老师。只返回JSON。", prompt)
    try:
        if "```" in result: result = result.split("```")[1].replace("json", "", 1)
        return json.loads(result.strip())
    except json.JSONDecodeError:
        return {"status": "normal", "comment": "已记录", "suggestion": ""}


# ── 4. 学习建议 ──

STUDY_ADVICE_PROMPT = """你是严格的考研监督老师。根据学生的学习汇报，给出下一步建议。

学生汇报: {report}
学习评分: 完成率{completion}% 及时率{timeliness}% 连续{streak}天

给出:
1. 一句话评价
2. 下一步具体建议(1-2条)
3. 需要加强的地方

格式: 简短段落，不超过100字。"""


def generate_study_advice(report: str, completion: float, timeliness: float, streak: int) -> str:
    prompt = STUDY_ADVICE_PROMPT.format(report=report, completion=completion,
                                         timeliness=timeliness, streak=streak)
    result = _call_deepseek("严格的考研监督老师。", prompt)
    return result.strip() if result else "继续保持，加油！"
