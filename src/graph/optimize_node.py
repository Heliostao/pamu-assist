"""
optimize 节点：解析 optimize_plan 工具结果（ToolMessage），执行检索并写 retrieved_docs。

与普通路径（tools → format）不同：split/both 走 retrieve_sub_queries 合并检索。
工具的真实执行（rewrite / split）已由 ToolNode 完成，本节点只负责解析 JSON 与检索，
tool_call_id 的配对、ToolMessage 的生成全部交给 ToolNode，不再手搓。
"""
import json

from langchain_core.messages import ToolMessage

from src.graph.state import RagState
from src.tools.rag_tool import retrieve_knowledge, retrieve_sub_queries


def optimize(state: RagState) -> dict:
    # ToolNode 已自动生成 ToolMessage，读最后一条即可；异常路径回退扫描
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

    if sub_queries:
        result_json = retrieve_sub_queries(sub_queries, retrieval_query)
    else:
        result_json = retrieve_knowledge.invoke({"query": retrieval_query})

    try:
        docs = json.loads(result_json) if result_json else []
    except json.JSONDecodeError:
        docs = []

    return {
        "retrieval_query": retrieval_query,
        "optimization_type": str(plan.get("optimization_type", "")),
        "sub_queries": sub_queries,
        "retrieved_docs": docs,
    }
