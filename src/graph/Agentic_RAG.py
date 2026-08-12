"""
Agentic RAG 工作流

START → chatbot（LLM 决策 + 帕姆人设）
         ├─ 无 tool_call → END（直接人设回复）
         └─ 有 tool_call → tools（ToolNode 执行检索）
                              ↓
                         grade（评估相关性 + 生成回答）
                              ↓
                             END
"""
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langgraph.constants import START, END
from langgraph.config import get_stream_writer
from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition

from src.models.llm import llm
from src.prompts import SYSTEM_PROMPT
from src.prompts import GRADE_PROMPT_TEMPLATE
from src.tools.rag_tool import retrieve_knowledge

# 工具节点
tools = [retrieve_knowledge]
llm_with_tools = llm.bind_tools(tools)
tool_node = ToolNode(tools)


# 聊天节点
def chatbot(state: MessagesState) -> dict:
    writer = get_stream_writer()
    chunks = []
    for chunk in llm_with_tools.stream(
        [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    ):
        chunks.append(chunk)
        if getattr(chunk, "content", ""):
            writer({"t": chunk.content})
    # 聚合 chunk，保留完整 tool_calls 供 tools_condition 判断
    response = chunks[0]
    for c in chunks[1:]:
        response = response + c
    return {"messages": [response]}


# 评估节点：评估检索结果 + 生成回答
def grade(state: MessagesState) -> dict:
    # 从 messages 中提取用户问题（最后一条 HumanMessage）
    question = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            question = msg.content
            break

    # 从 messages 中提取检索结果（最后一条 ToolMessage）
    context = ""
    for msg in reversed(state["messages"]):
        if hasattr(msg, "tool_call_id"):
            context = msg.content
            break

    question_summary = question[:20] + ("..." if len(question) > 20 else "")
    prompt = GRADE_PROMPT_TEMPLATE.format(
        question=question,
        context=context,
        question_summary=question_summary,
    )
    writer = get_stream_writer()
    full = ""
    for chunk in llm.stream(prompt):
        if getattr(chunk, "content", ""):
            writer({"t": chunk.content})
            full += chunk.content
    return {"messages": [AIMessage(content=full)]}


builder = StateGraph(MessagesState)
builder.add_node("chatbot", chatbot)
builder.add_node("tools", tool_node)
builder.add_node("grade", grade)

builder.add_edge(START, "chatbot")
builder.add_conditional_edges(
    "chatbot",
    tools_condition,
    {"tools": "tools", END: END},
)
builder.add_edge("tools", "grade")
builder.add_edge("grade", END)

graph = builder.compile()
