"""
RAG 检索工具

"""
import hashlib
import json

from langchain_core.documents import Document
from langchain_core.tools import tool

from src.auth.redis_client import get_client
from src.reranker import reranker
from src.retriever import compression_retriever
from src.retriever.vector_retriever import vector_retriever
from src.util.config import RAG_CACHE_ENABLED, RAG_CACHE_TTL

# 兼容阶段 0 评估脚本（scripts/eval_ragas.py 引用 _compression_retriever）：
# 向量召回 + 重排即"压缩检索"链路
_compression_retriever = compression_retriever


def build_search_query(query: str, character_name: str = "") -> str:
    """拼装实际检索词（工具与工作流节点复用，保证检索与缓存 key 一致）。"""
    parts = [p for p in (character_name.strip(), query.strip()) if p]
    return " ".join(parts)


def normalize(s: str) -> str:
    """规范化缓存 key：去首尾空白、折叠连续空白、统一小写。"""
    return " ".join(s.split()).lower()


def cache_key(search_query: str) -> str:
    return f"rag:{normalize(search_query)}"


def get_cache(search_query: str) -> str | None:
    if not RAG_CACHE_ENABLED:
        return None
    try:
        return get_client().get(cache_key(search_query))
    except Exception:
        return None


def set_cache(search_query: str, value: str) -> None:
    if not RAG_CACHE_ENABLED:
        return
    try:
        get_client().setex(cache_key(search_query), RAG_CACHE_TTL, value)
    except Exception:
        pass


def format_docs(docs) -> str:
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

    cached = get_cache(search_query)
    if cached is not None:
        return cached

    docs = _compression_retriever.invoke(search_query)
    result = format_docs(docs)
    set_cache(search_query, result)
    return result


def retrieve_sub_queries(sub_queries: list[str], rerank_query: str) -> str:
    """多 query 合并检索：各子 query 独立向量召回 → 按内容去重合并 → 统一重排。

    供 optimize 节点（split / both 路径）使用，避免每个子问题各自重排的重复开销。
    返回与 retrieve_knowledge 一致的 JSON 数组字符串；子查询为低频路径，不做 Redis 缓存。
    """
    seen: dict[str, Document] = {}
    for q in sub_queries:
        # 每个子 query 召回前 5 条候选，控制合并后总量（文档 4.4：各取 topK）
        for doc in vector_retriever.invoke(q)[:5]:
            seen.setdefault(doc.page_content.strip(), doc)
    if not seen:
        return "[]"
    reranked = reranker.compress_documents(
        documents=list(seen.values()),
        query=rerank_query,
    )
    return format_docs(reranked)
