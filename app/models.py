# app/models.py (Detail Version 반영)

from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey, Enum, DateTime, Text
from sqlalchemy.orm import relationship
from app.database import Base
import enum
from datetime import datetime

# --- Enums (기획서 반영) ---
class VisaType(str, enum.Enum):
    D2 = "D-2"
    D4 = "D-4"

# 상태(Status): 처리 단계 세분화
class StepStatus(str, enum.Enum):
    WAITING = "대기"          # 요청 생성, 처리 전
    REQUEST_DATA = "자료요청" # 추가 첨부 필요
    IN_REVIEW = "검토중"      # 전문가/운영 검토 진행
    IN_PROGRESS = "진행중"    # 실제 업무 처리 단계
    COMPLETED = "완료"        # 해당 단계 종료
    ON_HOLD = "보류"          # 사용자 사정으로 일시 중단

class DocStatus(str, enum.Enum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    REVIEW_NEEDED = "REVIEW_NEEDED"

# --- Tables ---

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    roadmap = relationship("Roadmap", back_populates="user", uselist=False)
    documents = relationship("Document", back_populates="user")
    posts = relationship("BoardPost", back_populates="author")

class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    full_name = Column(String)
    nationality = Column(String)
    visa_type = Column(Enum(VisaType))
    university = Column(String)
    entry_date = Column(Date)
    
    user = relationship("User", back_populates="profile")

class Roadmap(Base):
    __tablename__ = "roadmaps"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    steps = relationship("RoadmapStep", back_populates="roadmap")
    user = relationship("User", back_populates="roadmap")

class RoadmapStep(Base):
    __tablename__ = "roadmap_steps"
    id = Column(Integer, primary_key=True, index=True)
    roadmap_id = Column(Integer, ForeignKey("roadmaps.id"))
    
    title = Column(String)       # 단계명
    category = Column(String)    # 분류 (VISA, BANK, HOUSING 등)
    description = Column(String) # 설명
    
    # [워크플로우 핵심]
    status = Column(Enum(StepStatus), default=StepStatus.WAITING)
    order_index = Column(Integer)
    deadline = Column(Date)
    
    # 전문가 피드백/질문 (Question)
    expert_comment = Column(Text, nullable=True) 
    
    roadmap = relationship("Roadmap", back_populates="steps")

    # ▼ [추가] 댓글(Q&A)과의 관계 설정
    comments = relationship("StepComment", back_populates="step", cascade="all, delete-orphan")

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    doc_type = Column(String)
    s3_key = Column(String)
    upload_date = Column(DateTime, default=datetime.utcnow)
    
    # [3. 보관함 기능] 유효기간 및 리스크 분석
    expiry_date = Column(Date, nullable=True) 
    risk_analysis = Column(Text, nullable=True) # JSON 형태 저장
    verification_status = Column(Enum(DocStatus), default=DocStatus.UNVERIFIED)

    user = relationship("User", back_populates="documents")

# [3. 보관함 - 신뢰 장치] 감사 로그
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String) # "VIEW_DOC", "DOWNLOAD_DOC", "STATUS_CHANGE"
    target_id = Column(Integer) # 문서 ID or 스텝 ID
    timestamp = Column(DateTime, default=datetime.utcnow)

# [4. 커뮤니티]
class BoardPost(Base):
    __tablename__ = "board_posts"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    content = Column(String)
    author_id = Column(Integer, ForeignKey("users.id"))
    
    # ▼ [추가] 필터링과 결과 태그를 위한 컬럼
    visa_type = Column(String, default="D-2")  # 예: D-2, D-4
    result_tag = Column(String, default="TIP") # 예: SUCCESS(승인), FAIL(반려), TIP(정보)

    comments = relationship("BoardComment", back_populates="post")
    author = relationship("User", back_populates="posts")

class BoardComment(Base):
    __tablename__ = "board_comments"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(String)
    post_id = Column(Integer, ForeignKey("board_posts.id"))
    author_id = Column(Integer, ForeignKey("users.id"))
    post = relationship("BoardPost", back_populates="comments")

class StepComment(Base):
    __tablename__ = "step_comments"

    id = Column(Integer, primary_key=True, index=True)
    step_id = Column(Integer, ForeignKey("roadmap_steps.id"))
    author_id = Column(Integer, ForeignKey("users.id")) # 질문한 사람 (혹은 답변한 전문가)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    step = relationship("RoadmapStep", back_populates="comments")