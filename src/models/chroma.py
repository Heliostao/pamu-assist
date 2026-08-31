"""
Chroma
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
