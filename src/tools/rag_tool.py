"""
RAG 检索工具
将向量检索 + CrossEncoder 重排封装为单一 LangChain Tool，
供 LangGraph Agentic RAG 工作流中的 ToolNode 调用。
"""
from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_core.tools import tool

from src.models.chroma import vectorstore
from src.util.config import RERANKER_MODEL_DIR

_cross_encoder = HuggingFaceCrossEncoder(
    model_name=RERANKER_MODEL_DIR,
    model_kwargs={"device": "cpu"},
)

_reranker = CrossEncoderReranker(
    model=_cross_encoder,
    top_n=5,
)

_base_retriever = vectorstore.as_retriever(
    search_type="similarity_score_threshold",
    search_kwargs={"k": 8, "score_threshold": 0.35},
)

_compression_retriever = ContextualCompressionRetriever(
    base_compressor=_reranker,
    base_retriever=_base_retriever,
)


@tool
def retrieve_knowledge(character_name: str, aspect: str = "") -> str:
    """在崩坏：星穹铁道角色知识库中检索信息。

    适用场景：角色技能、行迹、星魂、背景故事、属性等一切与游戏角色相关的内容。
    传入角色名和查询方面，返回重排后的相关知识片段。

    Args:
        character_name: 用户询问的角色名称，如"黄泉""爻光""白厄"。
        aspect: 用户询问的具体方面，如"技能""背景故事""属性""星魂"。
                若用户泛问角色整体信息，留空即可。
    """
    query = f"{character_name} {aspect}".strip()
    docs = _compression_retriever.invoke(query)
    if not docs:
        return f"知识库中未找到关于「{character_name}」的相关内容。"
    lines = []
    for doc in docs:
        tag = doc.metadata.get("doc_type", "角色数据")
        lines.append(f"[{tag}] {doc.page_content}")
    return "\n\n".join(lines)
