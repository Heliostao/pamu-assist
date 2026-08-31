"""
optimize_plan 真实工具：判断并执行查询优化，输出结构化检索计划（JSON）。

由 ToolNode 统一执行：工具内完成 rewrite（结合多轮历史消解指代）与 split（拆分
子问题），返回 {"optimization_type", "retrieval_query", "sub_queries"}，
ToolNode 自动生成对应 ToolMessage，optimize 节点解析该 JSON 并执行检索。
"""
import json
from typing import Annotated

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from src.models.llm import llm
from src.prompts import REWRITE_PROMPT, SPLIT_PROMPT_TEMPLATE


def _last_question(messages: list) -> str:
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg.content
    return ""


def _rewrite(messages: list, character: str = "") -> str:
    """结合对话历史把口语化 / 带指代的提问改写为可检索 query。

    注入当前会话锁定的角色，约束指代词指向，防止"她/他"漂移到其他角色。
    """
    prompt = [
        SystemMessage(content=REWRITE_PROMPT.format(character=character or "未锁定"))
    ] + messages[-8:]
    resp = llm.invoke(prompt)
    return (resp.content or "").strip()


def _parse_json_array(text: str) -> list[str]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            return [str(x).strip() for x in data if str(x).strip()]
    except json.JSONDecodeError:
        pass
    # 兜底：截取首个 [...] 包裹的 JSON 段
    start, end = cleaned.find("["), cleaned.rfind("]")
    if start != -1 and end > start:
        try:
            data = json.loads(cleaned[start : end + 1])
            if isinstance(data, list):
                return [str(x).strip() for x in data if str(x).strip()]
        except json.JSONDecodeError:
            pass
    return []


def _split(question: str) -> list[str]:
    """把复杂问题拆成多个可独立检索的子问题。"""
    resp = llm.invoke(SPLIT_PROMPT_TEMPLATE.format(question=question))
    return _parse_json_array(resp.content or "")


@tool
def optimize_plan(
    optimization_type: str,
    state: Annotated[dict, InjectedState],
) -> str:
    """判断用户提问是否需要查询优化，并输出优化后的检索计划（JSON）。

    调用后工作流按该计划执行检索：rewrite 结果作为单 query 检索，
    split 结果作为子查询分别召回再合并。

    Args:
        optimization_type: 优化方式。取值：
            - "rewrite"：问题口语化或含指代（"她""他""这个角色"），改写为规范化检索 query；
            - "split"：问题含多个独立子问题，拆分后分别检索再合并；
            - "both"：既口语化/带指代、又含多个子问题，先改写再拆分。
    """
    messages = list(state["messages"])
    if messages and isinstance(messages[-1], AIMessage) and messages[-1].tool_calls:
        messages = messages[:-1]

    question = _last_question(messages)
    character = str(state.get("character") or "")
    if optimization_type in ("rewrite", "both"):
        retrieval_query = _rewrite(messages, character) or question
    else:
        retrieval_query = question

    sub_queries = _split(retrieval_query) if optimization_type in ("split", "both") else []
    return json.dumps(
        {
            "optimization_type": optimization_type,
            "retrieval_query": retrieval_query,
            "sub_queries": sub_queries,
        },
        ensure_ascii=False,
    )
