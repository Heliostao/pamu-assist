"""
router 节点：用 Cloudflare Clef 决策模型对用户问题做「是否需要检索」的二分意图路由。

输出 route：P(需要检索) >= ROUTER_RAG_THRESHOLD 判为 "rag"，否则判为 "chat"。
"""
from langchain_core.messages import HumanMessage

from src.graph.state import RagState
from src.models.clef import needs_rag
from src.util.config import ROUTER_RAG_THRESHOLD


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


def router(state: RagState) -> dict:
    character = state.get("character") or ""
    state_text = _build_state_text(state["messages"], character)
    p_rag = needs_rag(state_text)
    route = "rag" if p_rag >= ROUTER_RAG_THRESHOLD else "chat"
    return {"route": route}
