"""
Reranker 初始化：CrossEncoder 模型 + LangChain 重排器。

重排是链路中最耗时的一步，这里只负责初始化实例；具体编排（召回后精排）
由 retriever.compression_retriever 统一负责，本模块不依赖 retriever，避免循环引用。
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
