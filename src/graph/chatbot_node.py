"""
chatbot 节点：帕姆人设闲聊回复（chat 路径，router 判定为无需检索后到达）。
"""
from langchain_core.messages import SystemMessage
from langgraph.types import StreamWriter

from src.graph.state import RagState
from src.models.llm import llm
from src.prompts import PERSONA_PROMPT


def chatbot(state: RagState, writer: StreamWriter) -> dict:
    chunks = []
    for chunk in llm.stream([SystemMessage(content=PERSONA_PROMPT)] + state["messages"]):
        chunks.append(chunk)
        if getattr(chunk, "content", ""):
            writer({"t": chunk.content})
    # 聚合 chunk：保留完整响应
    response = chunks[0]
    for c in chunks[1:]:
        response = response + c
    return {"messages": [response]}
