# app/schemas.py (최종 수정 버전)

from pydantic import BaseModel, EmailStr
from datetime import date, datetime # <--- datetime 추가됨
from typing import Optional, List
from app.models import VisaType, StepStatus

# --- 1. 유저 프로필 입력용 (회원가입 시 받는 정보) ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    nationality: str
    visa_type: VisaType  # "D-2", "D-4" 등
    university: Optional[str] = None
    entry_date: date

# --- [New] 로드맵 단계별 댓글(Q&A) 스키마 (RoadmapStepResponse보다 먼저 와야 함) ---
class StepCommentBase(BaseModel):
    content: str

class StepCommentCreate(StepCommentBase):
    pass

class StepCommentResponse(StepCommentBase):
    id: int
    author_id: int
    created_at: datetime
    class Config:
        from_attributes = True

# --- 2. 로드맵 단계 출력용 (앱에 보여줄 정보) ---
class RoadmapStepResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: StepStatus
    order_index: int
    deadline: Optional[date] = None
    category: str
    
    # [New] 이 단계에 달린 댓글(티켓) 리스트
    comments: List[StepCommentResponse] = [] 

    class Config:
        from_attributes = True # (구 orm_mode)

# --- 3. 최종 응답용 (유저 정보 + 생성된 로드맵) ---
class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    
    class Config:
        from_attributes = True

# --- 4. 로드맵 전체 조회용 (로드맵 정보 + 단계 리스트) ---
class RoadmapResponse(BaseModel):
    id: int
    title: str
    steps: List[RoadmapStepResponse] = [] # 위에서 정의한 StepResponse 사용

    class Config:
        from_attributes = True

# --- 5. 커뮤니티용 스키마 ---
class CommentBase(BaseModel):
    content: str

class CommentCreate(CommentBase):
    pass

class CommentResponse(CommentBase):
    id: int
    author_id: int
    class Config:
        from_attributes = True

class PostBase(BaseModel):
    title: str
    content: str
    visa_type: str
    result_tag: str

class PostCreate(PostBase):
    pass

class PostResponse(PostBase):
    id: int
    author_id: int
    comments: List[CommentResponse] = [] # 게시글 볼 때 댓글도 같이 봄
    class Config:
        from_attributes = True