"""
压缩检索器：向量召回 + CrossEncoder 重排。

组装链：
    vector_retriever ─→ ContextualCompressionRetriever → Reranker 精排

tools 包只需引用本模块导出的 compression_retriever，无需关心底层链路。
"""
from langchain_classic.retrievers import ContextualCompressionRetriever

from src.reranker import reranker
from src.retriever.vector_retriever import vector_retriever

compression_retriever = ContextualCompressionRetriever(
    base_compressor=reranker,
    base_retriever=vector_retriever,
)
