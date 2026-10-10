"""
router 节点：用 Cloudflare Clef 决策模型做三层意图决策（一次调用）。

三层：needs_rag（是否检索）/ needs_optimize（是否优化）/ how（怎么优化）。
层级短路：chat 直接走聊天，direct 直接走检索，都不看后续层。
某层置信度低于 ROUTER_CONFIDENCE_THRESHOLD 时兜底到 decision 节点（DeepSeek）。
"""
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import StreamWriter

from src.graph.state import RagState
from src.models.clef import route_intent
from src.tools.rag_tool import detect_character
from src.util.config import ROUTER_CONFIDENCE_THRESHOLD


def _last_question(messages: list) -> str:
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg.content
    return ""


def _build_state_text(messages: list, character: str) -> str:
    lines = ["这是崩坏：星穹铁道游戏的玩家问答。"]
    if character:
        lines.append(
            f"当前对话已锁定角色为{character}，用户用「她」「他」等指代词时指代的就是该角色。"
        )
    lines.append(f"用户最新问题：{_last_question(messages)}")
    return "\n".join(lines)


def _retrieve_tool_call(state: RagState) -> AIMessage:
    question = _last_question(state["messages"])
    character = state.get("character") or ""
    locked = detect_character(question, character)
    return AIMessage(
        content="",
        tool_calls=[{
            "name": "retrieve_knowledge",
            "args": {"query": question, "character_name": locked},
            "id": "router_retrieve",
        }],
    )


def _optimize_tool_call(optimization_type: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{
            "name": "optimize_plan",
            "args": {"optimization_type": optimization_type},
            "id": "router_optimize",
        }],
    )


def router(state: RagState, writer: StreamWriter) -> dict:
    character = state.get("character") or ""
    state_text = _build_state_text(state["messages"], character)
    answers = route_intent(state_text)

    # 第一层：needs_rag
    l1 = answers["needs_rag"]
    if l1.get("confidence", 0) < ROUTER_CONFIDENCE_THRESHOLD:
        return {"route": "decision"}
    if l1["choice"] == "chat":
        return {"route": "chatbot"}

    # 第二层：needs_optimize
    l2 = answers["needs_optimize"]
    if l2.get("confidence", 0) < ROUTER_CONFIDENCE_THRESHOLD:
        return {"route": "decision"}
    if l2["choice"] == "direct":
        writer({"t": "让帕姆找找帕！\n"})
        return {"route": "tools", "messages": [_retrieve_tool_call(state)]}

    # 第三层：how
    l3 = answers["how"]
    if l3.get("confidence", 0) < ROUTER_CONFIDENCE_THRESHOLD:
        return {"route": "decision"}
    how = l3["choice"] if l3["choice"] in ("rewrite", "split", "both") else "rewrite"
    writer({"t": "让帕姆找找帕！\n"})
    return {"route": "tools", "messages": [_optimize_tool_call(how)]}
