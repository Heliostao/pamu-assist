"""
从 .env 加载所有配置项，不硬编码任何路径或密钥。
"""
import os

from dotenv import load_dotenv

load_dotenv()

# ── 模型一律从本地 HuggingFace 缓存加载（生产环境无法访问 huggingface.co，始终离线）──
# setdefault 不覆盖 .env 中已有的显式配置
os.environ.setdefault("HF_HUB_OFFLINE", "1")

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
