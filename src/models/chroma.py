"""
Chroma 向量数据库 + Embedding 模型

"""
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from src.util import (
    CHROMA_PERSIST_DIR,
    CHROMA_COLLECTION_NAME,
    EMBEDDING_MODEL_DIR,
)

embeddings = HuggingFaceEmbeddings(
    model_name=EMBEDDING_MODEL_DIR,
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)

vectorstore = Chroma(
    persist_directory=CHROMA_PERSIST_DIR,
    embedding_function=embeddings,
    collection_name=CHROMA_COLLECTION_NAME,
    collection_metadata={"hnsw:space": "cosine"},
)
