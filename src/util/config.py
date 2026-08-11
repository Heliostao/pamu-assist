"""
从 .env 加载所有配置项，不硬编码任何路径或密钥。
"""
import os

from dotenv import load_dotenv

load_dotenv()

# ── DeepSeek 大模型 ──
DEEPSEEK_MODEL_NAME = os.getenv("DEEPSEEK_MODEL_NAME", "deepseek-chat")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

# ── Chroma 向量数据库 ──
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8082"))
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "gamelore_rag")

# ── Embedding 模型（本地路径或 HuggingFace repo id） ──
EMBEDDING_MODEL_DIR = os.getenv("EMBEDDING_MODEL_DIR", "BAAI/bge-base-zh-v1.5")

# ── Reranker 模型（本地路径或 HuggingFace repo id） ──
RERANKER_MODEL_DIR = os.getenv("RERANKER_MODEL_DIR", "BAAI/bge-reranker-base")
