"""
format 节点：解析 ToolMessage 中的结构化检索结果，写入全局状态。

仅普通路径（tools → format）
"""
import json

from langchain_core.messages import AIMessage, ToolMessage

from src.graph.state import RagState
from src.tools.rag_tool import build_search_query, extract_character


def format_docs(state: RagState) -> dict:
    retrieval_query = ""
    retrieved_docs = []

    for msg in state["messages"]:
        if isinstance(msg, AIMessage):
            # 从工具调用参数还原实际检索词
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

    updates = {
        "retrieved_docs": retrieved_docs,
        "retrieval_query": retrieval_query,
    }
    # 从文档来源反推角色名，动态更新会话锁定的角色（无角色文档时保持原值）
    character = extract_character(retrieved_docs)
    if character:
        updates["character"] = character
    return updates
