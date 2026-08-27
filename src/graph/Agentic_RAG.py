"""
Agentic RAG 工作流（纯组装层）

只负责：注册节点 + 连边 + compile，不包含任何节点逻辑。
节点实现见同目录 chatbot_node / optimize_node / format_node / grade_node，
条件边路由见 routing。

流程：
START → chatbot（LLM 决策 + 帕姆人设）
         ├─ 无 tool_call → END（直接人设回复）
         └─ 有 tool_call → tools（ToolNode 统一执行）
              ├─ retrieve_knowledge → format（普通路径）→ grade → END
              └─ optimize_plan → optimize（解析工具结果 + 检索）→ grade → END
"""
from langgraph.constants import END, START
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode

from src.graph import routing
from src.graph.chatbot_node import chatbot
from src.graph.format_node import format_docs
from src.graph.grade_node import grade
from src.graph.optimize_node import optimize
from src.graph.state import RagState
from src.tools.optimize_plan import optimize_plan
from src.tools.rag_tool import retrieve_knowledge

tools = [retrieve_knowledge, optimize_plan]
tool_node = ToolNode(tools)

builder = StateGraph(RagState)
builder.add_node("chatbot", chatbot)
builder.add_node("tools", tool_node)
builder.add_node("optimize", optimize)
builder.add_node("format", format_docs)
builder.add_node("grade", grade)

builder.add_edge(START, "chatbot")
builder.add_conditional_edges(
    "chatbot",
    routing.route_after_chatbot,
    {"tools": "tools", END: END},
)
builder.add_conditional_edges(
    "tools",
    routing.route_after_tools,
    {"format": "format", "optimize": "optimize", END: END},
)
builder.add_edge("optimize", "grade")
builder.add_edge("format", "grade")
builder.add_edge("grade", END)

graph = builder.compile()
