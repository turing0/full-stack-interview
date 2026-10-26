from pathlib import Path

from sqlalchemy import create_engine, URL
from sqlalchemy.orm import declarative_base, sessionmaker

# 固定使用 backend/data.db，避免工作目录变化时误建空数据库。
SQLALCHEMY_DATABASE_URL = URL.create(
    "sqlite", database=str(Path(__file__).resolve().parent / "data.db")
)

# 创建数据库引擎
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# 获取数据库会话，并在请求结束后自动关闭连接
def get_db():
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()
