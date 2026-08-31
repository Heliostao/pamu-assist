"""Redis 客户端：验证码存取（db 8，5 分钟过期）。"""
import random

import redis

from src.util.config import REDIS_DB, REDIS_HOST, REDIS_PORT

CODE_TTL_SECONDS = 300  # 5 分钟
CODE_MIN_INTERVAL_SECONDS = 60  # 同一邮箱两次发码的最小间隔

_client: redis.Redis | None = None


def get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis(
            host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True
        )
    return _client


def gen_code() -> str:
    """生成 6 位数字验证码。"""
    return f"{random.randint(0, 999999):06d}"


def save_code(email: str, code: str) -> None:
    get_client().setex(f"vcode:{email}", CODE_TTL_SECONDS, code)


def get_code(email: str) -> str | None:
    return get_client().get(f"vcode:{email}")


def delete_code(email: str) -> None:
    get_client().delete(f"vcode:{email}")


def can_resend(email: str) -> bool:
    """检查是否在 60s 冷却期内"""
    return get_client().ttl(f"vcode:{email}") < CODE_TTL_SECONDS - CODE_MIN_INTERVAL_SECONDS
