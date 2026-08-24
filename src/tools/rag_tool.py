"""
RAG 检索工具

将"向量召回 + CrossEncoder 重排"封装为单一 LangChain Tool，
供 LangGraph Agentic RAG 工作流的检索节点调用。

- 返回结构化 JSON 数组（doc_id / source / doc_type / score / content），
  由工作流节点解析后写入全局状态，供评估节点与响应溯源使用；
- 检索结果按规范化 query 缓存到 Redis（命中直接跳过向量检索与重排，
  重排是链路中最耗时的一步，收益最大）。
"""
import hashlib
import json

from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_core.tools import tool

from src.auth.redis_client import get_client
from src.models.chroma import vectorstore
from src.util.config import (
    RAG_CACHE_ENABLED,
    RAG_CACHE_TTL,
    RERANKER_MODEL_DIR,
    RERANK_TOP_N,
    RETRIEVAL_SCORE_THRESHOLD,
    RETRIEVAL_TOP_K,
)

_cross_encoder = HuggingFaceCrossEncoder(
    model_name=RERANKER_MODEL_DIR,
    model_kwargs={"device": "cpu"},
)

_reranker = CrossEncoderReranker(
    model=_cross_encoder,
    top_n=RERANK_TOP_N,
)

_base_retriever = vectorstore.as_retriever(
    search_type="similarity_score_threshold",
    search_kwargs={"k": RETRIEVAL_TOP_K, "score_threshold": RETRIEVAL_SCORE_THRESHOLD},
)

_compression_retriever = ContextualCompressionRetriever(
    base_compressor=_reranker,
    base_retriever=_base_retriever,
)


def build_search_query(query: str, character_name: str = "") -> str:
    """拼装实际检索词（工具与工作流节点复用，保证检索与缓存 key 一致）。"""
    parts = [p for p in (character_name.strip(), query.strip()) if p]
    return " ".join(parts)


def _normalize(s: str) -> str:
    """规范化缓存 key：去首尾空白、折叠连续空白、统一小写。"""
    return " ".join(s.split()).lower()


def _cache_key(search_query: str) -> str:
    return f"rag:{_normalize(search_query)}"


def _get_cache(search_query: str) -> str | None:
    if not RAG_CACHE_ENABLED:
        return None
    try:
        return get_client().get(_cache_key(search_query))
    except Exception:
        return None


def _set_cache(search_query: str, value: str) -> None:
    if not RAG_CACHE_ENABLED:
        return
    try:
        get_client().setex(_cache_key(search_query), RAG_CACHE_TTL, value)
    except Exception:
        pass


def _format_docs(docs) -> str:
    """把重排后的文档格式化为结构化 JSON 数组。"""
    items = []
    for doc in docs:
        content = doc.page_content or ""
        items.append(
            {
                "doc_id": hashlib.sha256(content.strip().encode("utf-8")).hexdigest()[:16],
                "source": doc.metadata.get("source", ""),
                "doc_type": doc.metadata.get("doc_type", "角色数据"),
                "score": round(float(doc.metadata.get("relevance_score", 0) or 0), 6),
                "content": content,
            }
        )
    return json.dumps(items, ensure_ascii=False)


@tool
def retrieve_knowledge(query: str, character_name: str = "") -> str:
    """在崩坏：星穹铁道知识库中检索信息。

    适用场景：角色技能、行迹、星魂、背景故事、属性，以及游戏术语、命途机制等一切与游戏相关的内容。

    Args:
        query: 完整的检索问题，如"欢愉命途的机制是什么"或"黄泉的战技效果"。
        character_name: 可选的限定角色名。若问题明确涉及某角色（如"她的星魂效果"），
                        提供角色名可提升检索精度；非角色问题留空即可。
    """
    search_query = build_search_query(query, character_name)

    cached = _get_cache(search_query)
    if cached is not None:
        return cached

    docs = _compression_retriever.invoke(search_query)
    result = _format_docs(docs)
    _set_cache(search_query, result)
    return result
