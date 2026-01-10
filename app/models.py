# app/models.py (체크리스트 기능 추가된 최종본)

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, Date, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import enum
from datetime import datetime

# --- Enums (기획서 반영, DB 저장 시 문자열로 사용될 수도 있음) ---
class VisaType(str, enum.Enum):
    D2 = "D-2"
    D4 = "D-4"

class StepStatus(str, enum.Enum):
    WAITING = "대기"
    REQUEST_DATA = "자료요청"
    IN_REVIEW = "검토중"
    IN_PROGRESS = "진행중"
    COMPLETED = "완료"
    ON_HOLD = "보류"

class DocStatus(str, enum.Enum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    REVIEW_NEEDED = "REVIEW_NEEDED"

# ---------------------------------------------------------
# 1. 사용자 (User) - 프로필 정보 통합됨
# ---------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True) # 아이디
    email = Column(String, unique=True, index=True)    # 이메일
    full_name = Column(String)                         # 이름
    hashed_password = Column(String)                   # 비밀번호

    is_admin = Column(Boolean, default=False)
    
    # [통합된 프로필 정보]
    nationality = Column(String, nullable=True)        # 국적
    visa_type = Column(String, nullable=True)          # 비자 타입
    entry_date = Column(Date, nullable=True)           # 입국일
    
    # [관계 설정]
    # 1:1 관계 (User <-> Roadmap)
    roadmap = relationship("Roadmap", back_populates="user", uselist=False)
    
    # 1:N 관계 (User <-> Documents, Posts, Comments, Logs)
    documents = relationship("Document", back_populates="user")
    posts = relationship("BoardPost", back_populates="author")
    comments = relationship("BoardComment", back_populates="author")
    step_comments = relationship("StepComment", back_populates="author")
    audit_logs = relationship("AuditLog", back_populates="user")

    # [NEW] 예약 내역 관계 추가 (Priority 3 권장사항 반영)
    # 이제 user.reservations 로 해당 유저의 예약 목록을 조회할 수 있습니다.
    reservations = relationship("Reservation", back_populates="user")

# (주의: class UserProfile은 삭제되었습니다!)

# ---------------------------------------------------------
# 2. 로드맵 (Roadmap)
# ---------------------------------------------------------
class Roadmap(Base):
    __tablename__ = "roadmaps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 관계 설정
    user = relationship("User", back_populates="roadmap")
    steps = relationship("RoadmapStep", back_populates="roadmap", cascade="all, delete-orphan")

class RoadmapStep(Base):
    __tablename__ = "roadmap_steps"

    id = Column(Integer, primary_key=True, index=True)
    roadmap_id = Column(Integer, ForeignKey("roadmaps.id"))
    
    title = Column(String)
    category = Column(String)     # ENTRY, HOUSING, VISA, BANK
    description = Column(String)
    status = Column(String, default="대기") # 대기, 진행중, 완료 등
    order_index = Column(Integer)
    deadline = Column(Date, nullable=True)
    
    # 관계 설정
    roadmap = relationship("Roadmap", back_populates="steps")
    comments = relationship("StepComment", back_populates="step", cascade="all, delete-orphan")
    
    # [NEW] 체크리스트 (1:N)
    checklist = relationship("StepChecklist", back_populates="step", cascade="all, delete-orphan")
    # [NEW] 이 단계에 첨부된 문서들
    documents = relationship("Document", back_populates="step", cascade="all, delete-orphan")

# [NEW] 체크리스트 테이블 (스케치 우측 하단 구현용)
class StepChecklist(Base):
    __tablename__ = "step_checklists"
    
    id = Column(Integer, primary_key=True, index=True)
    step_id = Column(Integer, ForeignKey("roadmap_steps.id"))
    
    item_content = Column(String)      # 예: "여권 사본", "재학증명서"
    is_checked = Column(Boolean, default=False) # 체크 여부
    
    step = relationship("RoadmapStep", back_populates="checklist")

# 단계별 질문/댓글 (Ticket System)
class StepComment(Base):
    __tablename__ = "step_comments"

    id = Column(Integer, primary_key=True, index=True)
    step_id = Column(Integer, ForeignKey("roadmap_steps.id"))
    author_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    step = relationship("RoadmapStep", back_populates="comments")
    author = relationship("User", back_populates="step_comments")

# ---------------------------------------------------------
# 3. 문서 (Document)
# ---------------------------------------------------------
class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    step_id = Column(Integer, ForeignKey("roadmap_steps.id"), nullable=True)
    
    doc_type = Column(String) # PASSPORT, ARC, SCHOOL_LETTER
    s3_key = Column(String)   # 파일 경로
    
    verification_status = Column(String, default="UNVERIFIED")
    risk_analysis = Column(Text, nullable=True) # AI 분석 결과 (JSON)
    expiry_date = Column(Date, nullable=True)   # 만료일
    
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    # 관계 설정
    user = relationship("User", back_populates="documents")

    step = relationship("RoadmapStep", back_populates="documents")

# ---------------------------------------------------------
# 4. 커뮤니티 (Board)
# ---------------------------------------------------------
class BoardPost(Base):
    __tablename__ = "board_posts"

    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(Integer, ForeignKey("users.id"))
    
    title = Column(String)
    content = Column(Text)
    visa_type = Column(String)  # D-2, D-4

    category = Column(String)
    result_tag = Column(String, nullable=True) # SUCCESS, FAIL, TIP
    is_verified = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 관계 설정 (User.posts 와 매칭)
    author = relationship("User", back_populates="posts")
    comments = relationship("BoardComment", back_populates="post", cascade="all, delete-orphan")

class BoardComment(Base):
    __tablename__ = "board_comments"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("board_posts.id"))
    author_id = Column(Integer, ForeignKey("users.id"))
    
    content = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 관계 설정
    post = relationship("BoardPost", back_populates="comments")
    author = relationship("User", back_populates="comments")

# ---------------------------------------------------------
# 5. 감사 로그 (Audit Log)
# ---------------------------------------------------------
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    action = Column(String) # LOGIN, UPLOAD, VIEW_ROADMAP
    target_id = Column(Integer, nullable=True) # 관련된 문서나 글 ID
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="audit_logs")

class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    partner_name = Column(String)       # 예약한 파트너/기관 이름
    reservation_date = Column(String)   # YYYY-MM-DD
    reservation_time = Column(String)   # HH:MM
    memo = Column(String, nullable=True)
    status = Column(String, default="CONFIRMED") # 예약 확정
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="reservations")