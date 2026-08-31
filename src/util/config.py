"""
从 .env 加载所有配置项
"""
import os

from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault("HF_HUB_OFFLINE", "1")

# 项目根目录（config.py 位于 src/util/，上溯两级即项目根
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# DeepSeek 大模型
DEEPSEEK_MODEL_NAME = os.getenv("DEEPSEEK_MODEL_NAME", "deepseek-chat")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

# Chroma 向量数据库（HTTP 模式，连接 Docker 中的 Chroma Server）
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "gamelore_rag")

# ── Embedding 模型（本地路径或 HuggingFace repo id） ──
EMBEDDING_MODEL_DIR = os.getenv("EMBEDDING_MODEL_DIR", "BAAI/bge-base-zh-v1.5")

# ── Reranker 模型（本地路径或 HuggingFace repo id） ──
RERANKER_MODEL_DIR = os.getenv("RERANKER_MODEL_DIR", "BAAI/bge-reranker-base")

# ── RAG 检索参数（向量召回 + 重排） ──
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "10"))
RETRIEVAL_SCORE_THRESHOLD = float(os.getenv("RETRIEVAL_SCORE_THRESHOLD", "0.35"))
RERANK_TOP_N = int(os.getenv("RERANK_TOP_N", "3"))

# ── 短期记忆：每次问答注入会话的历史消息条数 ──
RAG_HISTORY_LIMIT = int(os.getenv("RAG_HISTORY_LIMIT", "8"))

# ── RAG 评估日志（在线侧落盘，离线 RAGAS 脚本消费）──
EVAL_LOG_ENABLED = os.getenv("EVAL_LOG_ENABLED", "true").lower() == "true"
EVAL_LOG_DIR = os.getenv("EVAL_LOG_DIR", os.path.join(PROJECT_ROOT, "eval_data"))
# 日志采样率 0~1，评估成本控制时可调小
EVAL_SAMPLE_RATE = float(os.getenv("EVAL_SAMPLE_RATE", "1.0"))

# ── 认证与登录 ──
SECRET_KEY = os.getenv("SECRET_KEY", "pamu-assist-jwt-secret-change-me")
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))
JWT_ALGORITHM = "HS256"

# 默认账号（账号密码登录，账号密码均从 .env 读取）
DEFAULT_USERNAME = os.getenv("DEFAULT_USERNAME", "taogong")
DEFAULT_PASSWORD = os.getenv("DEFAULT_PASSWORD", "050425")

# SMTP（QQ 邮箱，发送验证码）
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.qq.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")

# Redis（验证码缓存）
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "8"))

# PostgreSQL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://pamu:050425@localhost:5433/pamu",
)
