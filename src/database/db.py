"""数据库连接与会话管理（SQLAlchemy 2.x + PostgreSQL）。"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.util.config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""


def get_db():
    """FastAPI 依赖：提供数据库会话并在请求结束后关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """建表"""
    from sqlalchemy import inspect, text

    from src.auth.security import hash_password
    from src.database import models  # noqa: F401  确保模型已注册
    from src.util.config import DEFAULT_PASSWORD, DEFAULT_USERNAME

    Base.metadata.create_all(bind=engine)

    # 已存在的 users 表补充 username 列
    insp = inspect(engine)
    if "users" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("users")}
        if "username" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR(64)"))
                conn.execute(
                    text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username)")
                )

    # 确保默认账号存在（账号密码登录，账号密码由 .env 配置）
    with SessionLocal() as db:
        if db.query(models.User).filter(models.User.username == DEFAULT_USERNAME).first() is None:
            db.add(
                models.User(
                    username=DEFAULT_USERNAME,
                    email=f"{DEFAULT_USERNAME}@local",
                    nickname=DEFAULT_USERNAME,
                    password_hash=hash_password(DEFAULT_PASSWORD),
                )
            )
            db.commit()
