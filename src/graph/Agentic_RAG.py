"""
Agentic RAG 工作流

START → chatbot（LLM 决策 + 帕姆人设）
         ├─ 无 tool_call → END（直接人设回复）
         └─ 有 tool_call → tools（标准 ToolNode：执行检索工具，召回 + 重排）
                              ↓
                         format（纯函数：解析 ToolMessage 中的结构化结果，写入全局状态）
                              ↓
                         grade（从全局状态读取检索结果，评估相关性 + 生成回答）
                              ↓
                             END
"""
import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.constants import END, START
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import StreamWriter

from src.graph.state import RagState
from src.models.llm import llm
from src.prompts import GRADE_PROMPT_TEMPLATE, SYSTEM_PROMPT
from src.tools.rag_tool import build_search_query, retrieve_knowledge

tools = [retrieve_knowledge]
llm_with_tools = llm.bind_tools(tools)
tool_node = ToolNode(tools)


# ── 决策节点：LLM 判断是否需要检索 ──
def chatbot(state: RagState, writer: StreamWriter) -> dict:
    chunks = []
    for chunk in llm_with_tools.stream(
        [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    ):
        chunks.append(chunk)
        if getattr(chunk, "content", ""):
            writer({"t": chunk.content})
    # 聚合 chunk：保留完整 tool_calls 供 tools_condition 判断
    response = chunks[0]
    for c in chunks[1:]:
        response = response + c
    return {"messages": [response]}


# ── 中间结果解析节点：读取 ToolMessage，解析结构化检索结果写入全局状态（纯函数） ──
def format_docs(state: RagState) -> dict:
    retrieval_query = ""
    retrieved_docs = []

    for msg in state["messages"]:
        if isinstance(msg, AIMessage):
            # 从工具调用参数还原实际检索词（兼作缓存 key 的记录）
            for tc in getattr(msg, "tool_calls", []) or []:
                if tc.get("name") == "retrieve_knowledge":
                    args = tc.get("args", {})
                    retrieval_query = build_search_query(
                        args.get("query", ""), args.get("character_name", "")
                    )
        elif isinstance(msg, ToolMessage):
            try:
                parsed = json.loads(msg.content)
                if isinstance(parsed, list):
                    retrieved_docs.extend(parsed)
            except json.JSONDecodeError:
                pass

    return {
        "retrieved_docs": retrieved_docs,
        "retrieval_query": retrieval_query,
    }


# ── 评估节点：从全局状态读取检索结果，评估相关性 + 生成回答 ──
def grade(state: RagState, writer: StreamWriter) -> dict:
    # 用户原始问题（最后一条 HumanMessage），用于相关性评估
    question = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            question = msg.content
            break

    # 从全局状态取检索结果（而非解析 ToolMessage）
    docs = state.get("retrieved_docs") or []
    context = "\n\n".join(
        f"[{d.get('doc_type', '角色数据')}] {d.get('content', '')}" for d in docs
    )

    question_summary = question[:20] + ("..." if len(question) > 20 else "")
    prompt = GRADE_PROMPT_TEMPLATE.format(
        question=question,
        context=context,
        question_summary=question_summary,
    )
    full = ""
    for chunk in llm.stream(prompt):
        if getattr(chunk, "content", ""):
            writer({"t": chunk.content})
            full += chunk.content
    return {"messages": [AIMessage(content=full)]}


builder = StateGraph(RagState)
builder.add_node("chatbot", chatbot)
builder.add_node("tools", tool_node)
builder.add_node("format", format_docs)
builder.add_node("grade", grade)

builder.add_edge(START, "chatbot")
builder.add_conditional_edges(
    "chatbot",
    tools_condition,
    {"tools": "tools", END: END},
)
builder.add_edge("tools", "format")
builder.add_edge("format", "grade")
builder.add_edge("grade", END)

graph = builder.compile()
