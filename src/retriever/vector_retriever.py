"""
向量检索器：基于 Chroma 的余弦相似度召回。

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
