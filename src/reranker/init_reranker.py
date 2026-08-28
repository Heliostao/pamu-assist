"""
Reranker
"""
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder

from src.util.config import RERANKER_MODEL_DIR, RERANK_TOP_N

cross_encoder = HuggingFaceCrossEncoder(
    model_name=RERANKER_MODEL_DIR,
    model_kwargs={"device": "cpu"},
)

reranker = CrossEncoderReranker(
    model=cross_encoder,
    top_n=RERANK_TOP_N,
)
