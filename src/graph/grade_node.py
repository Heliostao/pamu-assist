"""
grade 节点：从全局状态读取检索结果，评估相关性 + 生成回答。
"""
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import StreamWriter

from src.graph.state import RagState
from src.models.llm import llm
from src.prompts import GRADE_PROMPT_TEMPLATE
from src.tools.rag_tool import extract_character


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

    character = state.get("character") or ""
    doc_character = extract_character(docs)

    question_summary = question[:20] + ("..." if len(question) > 20 else "")
    prompt = GRADE_PROMPT_TEMPLATE.format(
        question=question,
        context=context,
        question_summary=question_summary,
        character=character or "未锁定",
        doc_character=doc_character or "未命中角色数据",
    )
    full = ""
    for chunk in llm.stream(prompt):
        if getattr(chunk, "content", ""):
            writer({"t": chunk.content})
            full += chunk.content
    return {"messages": [AIMessage(content=full)]}
