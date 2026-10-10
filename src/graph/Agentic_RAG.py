"""
Agentic RAG 工作流（纯组装层）

只负责：注册节点 + 连边 + compile，不包含任何节点逻辑。
节点实现见同目录 router_node / chatbot_node / decision_node / format_node /
optimize_node / grade_node，条件边路由见 routing。

流程：
START → router（Cloudflare Clef 二分：chat / rag）
         ├─ chat → chatbot（帕姆人设闲聊回复）→ END
         └─ rag  → decision（DeepSeek 判断直接检索 / 改写 / 拆分）
              ├─ 无 tool_call → END（clef 误判为 rag 的闲聊，直接人设回复）
              └─ 有 tool_call → tools（ToolNode 统一执行）
                   ├─ retrieve_knowledge → format → grade → END
                   └─ optimize_plan → optimize → grade → END
"""
from langgraph.constants import END, START
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode

from src.graph import routing
from src.graph.chatbot_node import chatbot
from src.graph.decision_node import decision
from src.graph.format_node import format_docs
from src.graph.grade_node import grade
from src.graph.optimize_node import optimize
from src.graph.router_node import router
from src.graph.state import RagState
from src.tools.optimize_plan import optimize_plan
from src.tools.rag_tool import retrieve_knowledge

tools = [retrieve_knowledge, optimize_plan]
tool_node = ToolNode(tools)

builder = StateGraph(RagState)
builder.add_node("router", router)
builder.add_node("chatbot", chatbot)
builder.add_node("decision", decision)
builder.add_node("tools", tool_node)
builder.add_node("format", format_docs)
builder.add_node("optimize", optimize)
builder.add_node("grade", grade)

builder.add_edge(START, "router")
builder.add_conditional_edges(
    "router",
    routing.route_after_router,
    {"chat": "chatbot", "rag": "decision"},
)
builder.add_edge("chatbot", END)
builder.add_conditional_edges(
    "decision",
    routing.route_after_decision,
    {"tools": "tools", END: END},
)
builder.add_conditional_edges(
    "tools",
    routing.route_after_tools,
    {"format": "format", "optimize": "optimize", END: END},
)
builder.add_edge("format", "grade")
builder.add_edge("optimize", "grade")
builder.add_edge("grade", END)

graph = builder.compile()
