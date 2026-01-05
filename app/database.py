# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. DB 주소 설정 (일단은 개발용으로 SQLite 사용, 나중에 PostgreSQL로 한 줄만 바꾸면 됨)
SQLALCHEMY_DATABASE_URL = "sqlite:///./settlo.db"
# PostgreSQL 예시: "postgresql://user:password@localhost/dbname"

# 2. 엔진 생성
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 3. 세션 생성 (실제 DB 작업용)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. 모델들의 조상(Base) 클래스 생성
Base = declarative_base()