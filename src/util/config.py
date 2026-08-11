"""
从 .env 加载所有配置项，不硬编码任何路径或密钥。
"""
import os

from dotenv import load_dotenv

load_dotenv()

# ── 项目根目录（config.py 位于 src/util/，上溯两级即项目根）──
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# ── DeepSeek 大模型 ──
DEEPSEEK_MODEL_NAME = os.getenv("DEEPSEEK_MODEL_NAME", "deepseek-chat")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

# ── Chroma 向量数据库（持久化模式，存储在项目根目录下）──
CHROMA_PERSIST_DIR = os.getenv(
    "CHROMA_PERSIST_DIR",
    os.path.join(PROJECT_ROOT, "chroma_data"),
)
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "gamelore_rag")

# ── Embedding 模型（本地路径或 HuggingFace repo id） ──
EMBEDDING_MODEL_DIR = os.getenv("EMBEDDING_MODEL_DIR", "BAAI/bge-base-zh-v1.5")

# ── Reranker 模型（本地路径或 HuggingFace repo id） ──
RERANKER_MODEL_DIR = os.getenv("RERANKER_MODEL_DIR", "BAAI/bge-reranker-base")
