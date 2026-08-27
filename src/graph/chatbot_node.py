"""
chatbot 节点：LLM 决策 + 帕姆人设流式输出。

绑定两个工具，均交由 ToolNode 统一执行：
- retrieve_knowledge：常规检索（问题规范、单点查询）；
- optimize_plan：真实工具，执行查询优化（rewrite / split / both），返回检索计划 JSON。
"""
from langchain_core.messages import SystemMessage
from langgraph.types import StreamWriter

from src.graph.state import RagState
from src.models.llm import llm
from src.prompts import SYSTEM_PROMPT
from src.tools.optimize_plan import optimize_plan
from src.tools.rag_tool import retrieve_knowledge

llm_with_tools = llm.bind_tools([retrieve_knowledge, optimize_plan])


def chatbot(state: RagState, writer: StreamWriter) -> dict:
    chunks = []
    for chunk in llm_with_tools.stream(
        [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    ):
        chunks.append(chunk)
        if getattr(chunk, "content", ""):
            writer({"t": chunk.content})
    # 聚合 chunk：保留完整 tool_calls 供路由判断
    response = chunks[0]
    for c in chunks[1:]:
        response = response + c
    return {"messages": [response]}
