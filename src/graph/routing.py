"""
自定义条件边：tool_call 统一进 ToolNode，再按 ToolMessage.name 分流。

langgraph 内置 tools_condition 只区分"有无 tool_call"，无法区分工具执行后的结果
由哪个节点解析，故拆成两层路由：
1. route_after_chatbot：有 tool_call 一律进 tools（ToolNode 统一执行），否则 END；
2. route_after_tools：按 ToolMessage.name 决定解析节点（format / optimize / END）。
"""
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.constants import END

from src.graph.state import RagState


def route_after_chatbot(state: RagState) -> str:
    """chatbot 之后：有 tool_call 一律进 tools，否则结束。"""
    last = state["messages"][-1]
    if not isinstance(last, AIMessage) or not last.tool_calls:
        return END
    return "tools"


def route_after_tools(state: RagState) -> str:
    """tools 之后：按 ToolMessage.name 分流，决定由哪个节点解析结果。"""
    for msg in reversed(state["messages"]):
        if isinstance(msg, ToolMessage):
            if msg.name == "retrieve_knowledge":
                return "format"
            if msg.name == "optimize_plan":
                return "optimize"
            # 未知工具名：保守结束（chatbot 已给出回复）
            return END
    return END
