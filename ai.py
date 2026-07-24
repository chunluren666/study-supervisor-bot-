# -*- coding: utf-8 -*-
"""
AI 模块——接入 DeepSeek API，处理任务识别、完成检查、抽查评估
"""

import json
import time
import urllib.request
import urllib.error
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


def _call_deepseek(system_prompt: str, user_message: str,
                   temperature: float = 0.3,
                   fallback: str = "{}") -> str:
    """调用 DeepSeek Chat API，返回文本回复。API 不可用时返回 fallback"""
    if not DEEPSEEK_API_KEY:
        return fallback

    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds

    for attempt in range(MAX_RETRIES):
        try:
            body = json.dumps({
                "model": DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "temperature": temperature,
                "max_tokens": 500,
            }).encode("utf-8")

            req = urllib.request.Request(
                f"{DEEPSEEK_BASE_URL}/chat/completions",
                data=body,
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                print(f"[AI] 重试 {attempt+1}/{MAX_RETRIES}: {e}")
                time.sleep(RETRY_DELAY)
            else:
                print(f"[AI] 放弃: {e}")
                return fallback


# ── 回退方案：正则匹配 ──

def _fallback_parse(msg: str) -> str:
    """当 API 不可用时，用简单的关键词匹配"""
    msg_lower = msg.lower()

    # 任务关键词
    # 先判断任务发布（关键词更强）
    if any(kw in msg for kw in ["任务", "今天完成", "提交", "截止", "负责"]):
        # 提取中文人名: "张三"在"负责"/"完成"之前
        import re
        names = list(set(re.findall(r'([一-龥]{2,4})(?=负责|完成|提交|和)', msg)))
        return json.dumps({
            "intent": "task_publish",
            "title": msg[:50],
            "content": msg,
            "deadline": None,
            "assignees": names,
        }, ensure_ascii=False)
    # 再判断任务完成
    if any(kw in msg for kw in ["完成了", "做完了", "好了", "搞定了", "提交了"]):
        return json.dumps({"intent": "task_complete", "task_hint": msg}, ensure_ascii=False)

    return json.dumps({"intent": "unknown"})


# ── 1. 任务发布识别 ──

TASK_PARSE_PROMPT = """你是一个学习监督助手的消息解析器。分析微信群消息，判断是否为任务发布。

如果是任务发布消息，提取信息并以JSON返回：
{"intent": "task_publish", "title": "任务标题简短10字内", "content": "完整描述", "deadline": "ISO时间或null", "assignees": ["被分配者"]}
如果不是任务发布：{"intent": "unknown"}
只返回JSON，不要其他内容。"""


def parse_task_message(message: str) -> dict:
    """解析消息是否为任务发布，返回结构化数据"""
    result = _call_deepseek(TASK_PARSE_PROMPT, message,
                            fallback=_fallback_parse(message))
    try:
        # 提取 JSON（可能被 markdown 包裹）
        if "```" in result:
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        return json.loads(result.strip())
    except json.JSONDecodeError:
        return {"intent": "unknown"}


# ── 2. 完成状态识别 ──

COMPLETE_CHECK_PROMPT = """你是一个严谨的学习监督助手。学生提交了任务完成声明，你需要审核证据是否充分。

任务要求：{task_content}
学生提交：{user_message}

审核规则：
1. 仅说"完成/好了/做完了"无具体内容 → need_more，要求提交具体证据（笔记、截图、代码、总结等）
2. 描述了部分完成（如"看了50%""做了一半"）→ rejected，说明"未完成，请继续"
3. 提供了具体成果 + 满足任务要求 → approved
4. 格式为：{{"decision": "approved或need_more或rejected", "reason": "简短理由", "quality": "good或ok或poor"}}

只返回JSON。"""


def check_completion(task_content: str, user_message: str) -> dict:
    """判断成员提交的完成内容是否合格"""
    prompt = COMPLETE_CHECK_PROMPT.format(
        task_content=task_content,
        user_message=user_message,
    )
    # 回退判断
    fallback = json.dumps(
        {"decision": "approved", "reason": "提交了内容", "quality": "ok"}
        if len(user_message) > 15 else
        {"decision": "need_more", "reason": "请提交具体内容", "quality": "poor"},
        ensure_ascii=False
    )
    result = _call_deepseek("你是一个严谨的学习监督助手。只返回JSON。", prompt,
                            fallback=fallback)
    try:
        if "```" in result:
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        return json.loads(result.strip())
    except json.JSONDecodeError:
        if len(user_message) > 15:
            return {"decision": "approved", "reason": "提交了较详细内容", "quality": "ok"}
        return {"decision": "need_more", "reason": "请提交具体内容", "quality": "poor"}


# ── 3. 抽查评估 ──

SPOT_CHECK_PROMPT = """你是一个学习监督助手。你抽查了某位成员，根据其回复评估学习状态。

抽查问题：{question}
成员回复：{answer}

以JSON返回：{{"status": "good或normal或warning", "comment": "评价", "suggestion": "建议"}}
只返回JSON。"""


def evaluate_spot_check(question: str, answer: str) -> dict:
    """评估抽查回复"""
    prompt = SPOT_CHECK_PROMPT.format(question=question, answer=answer)
    fallback = json.dumps({"status": "normal", "comment": "收到回复", "suggestion": ""},
                          ensure_ascii=False)
    result = _call_deepseek("你是一个严谨的学习监督助手。只返回JSON。", prompt,
                            fallback=fallback)
    try:
        if "```" in result:
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        return json.loads(result.strip())
    except json.JSONDecodeError:
        return {"status": "normal", "comment": "收到回复", "suggestion": ""}


# ── 测试 ──
if __name__ == "__main__":
    # 测试任务解析
    print("=== 测试任务解析 ===")
    test_msg = "今天完成数学第三章习题，晚上8点前提交"
    result = parse_task_message(test_msg)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    print("\n=== 测试完成检查 ===")
    result = check_completion("阅读论文并写500字总结", "完成")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    print("\n=== 测试完成检查(通过) ===")
    result = check_completion(
        "阅读论文并写500字总结",
        "论文主要讨论了Transformer架构在NLP中的应用，我整理了三个创新点：1.注意力机制..."
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
