
from langchain_classic.retrievers import ContextualCompressionRetriever

from src.reranker import reranker
from src.retriever.vector_retriever import vector_retriever

compression_retriever = ContextualCompressionRetriever(
    base_compressor=reranker,
    base_retriever=vector_retriever,
)
