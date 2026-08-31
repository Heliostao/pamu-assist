"""
optimize 节点：解析 optimize_plan 工具结果（ToolMessage），执行检索并写 retrieved_docs。

"""
import json

from langchain_core.messages import ToolMessage

from src.graph.state import RagState
from src.tools.rag_tool import (
    detect_character,
    extract_character,
    retrieve_knowledge,
    retrieve_sub_queries,
)


def optimize(state: RagState) -> dict:
    # ToolNode 已自动生成 ToolMessage
    tool_msg = state["messages"][-1]
    if not isinstance(tool_msg, ToolMessage):
        for msg in reversed(state["messages"]):
            if isinstance(msg, ToolMessage):
                tool_msg = msg
                break

    plan = {}
    try:
        plan = json.loads(tool_msg.content or "{}")
    except json.JSONDecodeError:
        plan = {}

    retrieval_query = str(plan.get("retrieval_query", ""))
    sub_queries = plan.get("sub_queries") or []

    # 实体锁定：query 已含已知角色名则用之（A→B 切换时跟随用户），
    # 否则回退会话当前角色（防 rewrite 漏写角色名导致检索漂移）
    character = state.get("character") or ""
    locked = detect_character(retrieval_query, character)

    if sub_queries:
        result_json = retrieve_sub_queries(sub_queries, retrieval_query)
    else:
        args: dict = {"query": retrieval_query}
        if locked:
            args["character_name"] = locked
        result_json = retrieve_knowledge.invoke(args)

    try:
        docs = json.loads(result_json) if result_json else []
    except json.JSONDecodeError:
        docs = []

    updates = {
        "retrieval_query": retrieval_query,
        "optimization_type": str(plan.get("optimization_type", "")),
        "sub_queries": sub_queries,
        "retrieved_docs": docs,
    }
    # 从文档来源反推角色名，动态更新会话锁定的角色（无角色文档时保持原值）
    new_character = extract_character(docs)
    if new_character:
        updates["character"] = new_character
    return updates
