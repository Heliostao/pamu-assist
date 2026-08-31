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
    # 动态注入会话锁定角色：指代消解与工具参数生成都以该角色为锚
    system_content = SYSTEM_PROMPT
    character = state.get("character") or ""
    if character:
        system_content += (
            f"\n\n当前对话已锁定角色「{character}」：用户用指代词（她/他）提问时指代的就是该角色；"
            f"调用 retrieve_knowledge 时应把 character_name 传为「{character}」，"
            f"调用 optimize_plan 改写时应保持该角色不变。"
        )

    chunks = []
    for chunk in llm_with_tools.stream(
        [SystemMessage(content=system_content)] + state["messages"]
    ):
        chunks.append(chunk)
        if getattr(chunk, "content", ""):
            writer({"t": chunk.content})
    # 聚合 chunk：保留完整 tool_calls 供路由判断
    response = chunks[0]
    for c in chunks[1:]:
        response = response + c
    return {"messages": [response]}
