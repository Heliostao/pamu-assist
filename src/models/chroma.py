"""
Chroma 向量数据库（HTTP 模式，连接 Docker 中的 Chroma Server）+ Embedding 模型

不再使用本地 chroma_data/ 目录，向量库由独立的 Chroma 服务（compose.yaml 中的
chroma 服务）提供，数据持久化在该容器挂载的 chroma_data 数据卷中。
"""
import chromadb
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from src.util import (
    CHROMA_HOST,
    CHROMA_PORT,
    CHROMA_COLLECTION_NAME,
    EMBEDDING_MODEL_DIR,
)

embeddings = HuggingFaceEmbeddings(
    model_name=EMBEDDING_MODEL_DIR,
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)

_chroma_client = chromadb.HttpClient(
    host=CHROMA_HOST,
    port=CHROMA_PORT,
)

vectorstore = Chroma(
    client=_chroma_client,
    embedding_function=embeddings,
    collection_name=CHROMA_COLLECTION_NAME,
    collection_metadata={"hnsw:space": "cosine"},
)
