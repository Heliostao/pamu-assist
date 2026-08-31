"""
RAG 检索工具

"""
import hashlib
import json
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.tools import tool

from src.reranker import reranker
from src.retriever import compression_retriever
from src.retriever.vector_retriever import vector_retriever
from src.util.config import PROJECT_ROOT

_compression_retriever = compression_retriever

_CHAR_DIR = Path(PROJECT_ROOT) / "data" / "character"
KNOWN_CHARACTERS = (
    sorted(p.stem for p in _CHAR_DIR.glob("*.md")) if _CHAR_DIR.is_dir() else []
)


def build_search_query(query: str, character_name: str = "") -> str:
    """拼装实际检索词（工具与工作流节点复用）。"""
    parts = [p for p in (character_name.strip(), query.strip()) if p]
    return " ".join(parts)


def extract_character(docs: list[dict]) -> str:
    """从检索文档反推角色名：取第一个 doc_type 为"角色数据"的 source（去掉 .md）。

    返回空串表示本次文档不涉及角色（如纯术语问题），调用方应保持原 character 不变。
    """
    for d in docs or []:
        if d.get("doc_type") == "角色数据":
            source = str(d.get("source", "")).strip()
            name = source[:-3] if source.endswith(".md") else source
            if name:
                return name
    return ""


def detect_character(query: str, fallback: str = "") -> str:
    """实体锁定：若 query 中出现知识库已知角色名则返回该角色（处理 A→B 切换）；
    否则回退到会话当前角色（防 rewrite 漏写角色名时检索漂移）。"""
    for name in KNOWN_CHARACTERS:
        if name and name in query:
            return name
    return fallback


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
    docs = _compression_retriever.invoke(search_query)
    return format_docs(docs)


def retrieve_sub_queries(sub_queries: list[str], rerank_query: str) -> str:
    """多 query 合并检索：各子 query 独立向量召回 → 按内容去重合并 → 统一重排。

    供 optimize 节点（split / both 路径）使用，避免每个子问题各自重排的重复开销。
    返回与 retrieve_knowledge 一致的 JSON 数组字符串。
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
