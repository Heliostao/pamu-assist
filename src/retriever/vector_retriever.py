"""
向量检索器：基于 Chroma 的余弦相似度召回。

职责单一：只负责"向量召回"这一件事，输出候选池（RETRIEVAL_TOP_K），
交给压缩检索层做 CrossEncoder 精排。
"""
from src.models.chroma import vectorstore
from src.util.config import RETRIEVAL_TOP_K, RETRIEVAL_SCORE_THRESHOLD

vector_retriever = vectorstore.as_retriever(
    search_type="similarity_score_threshold",
    search_kwargs={
        "k": RETRIEVAL_TOP_K,
        "score_threshold": RETRIEVAL_SCORE_THRESHOLD,
    },
)
