from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date, datetime

# [NEW] 문서 정보 간략 보기 스키마
class DocumentResponse(BaseModel):
    id: int
    user_id: int
    doc_type: str
    s3_key: str
    verification_status: str
    risk_analysis: Optional[str] = None
    uploaded_at: datetime
    
    class Config:
        from_attributes = True

# --- 0. 토큰 (로그인용) ---
class Token(BaseModel):
    access_token: str
    token_type: str
    
    # 프론트엔드 편의를 위해 추가한 필드들
    user_id: int
    user_name: str
    visa_type: Optional[str] = None
    is_admin: bool = False

class TokenData(BaseModel):
    username: Optional[str] = None

# --- 1. 유저 스키마 ---

# 회원가입 시 받는 정보
class UserCreate(BaseModel):
    username: str
    password: str
    email: EmailStr
    full_name: str

# 내 정보 업데이트용
class UserUpdate(BaseModel):
    nationality: Optional[str] = None
    visa_type: Optional[str] = None
    entry_date: Optional[date] = None

# 유저 정보 조회용
class User(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    nationality: Optional[str] = None
    visa_type: Optional[str] = None
    entry_date: Optional[date] = None
    is_admin: bool = False

    class Config:
        from_attributes = True

# --- 2. 로드맵/댓글/체크리스트 스키마 ---

# [NEW] 체크리스트 항목 응답용
class ChecklistItemResponse(BaseModel):
    id: int
    item_content: str
    is_checked: bool

    class Config:
        from_attributes = True

# [NEW] 체크리스트 상태 변경 요청용 (이게 없어서 에러가 났습니다!)
class ChecklistUpdate(BaseModel):
    is_checked: bool

# 단계별 댓글(티켓)
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

# 로드맵 단계 출력용
class RoadmapStepResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: str
    order_index: int
    deadline: Optional[date] = None
    category: str
    
    # 댓글과 체크리스트 포함
    comments: List[StepCommentResponse] = [] 
    checklist: List[ChecklistItemResponse] = []  # <--- 체크리스트 추가됨
    documents: List[DocumentResponse] = []

    class Config:
        from_attributes = True

# 로드맵 전체 조회용
class RoadmapResponse(BaseModel):
    id: int
    title: str
    steps: List[RoadmapStepResponse] = []

    class Config:
        from_attributes = True

# --- 3. 게시판/커뮤니티 스키마 ---

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

class PostCreate(BaseModel):
    title: str
    content: str
    visa_type: str
    category: str
    result_tag: Optional[str] = None

class PostResponse(BaseModel):
    id: int
    title: str
    content: str
    author_id: int
    visa_type: str
    category: str
    result_tag: Optional[str] = None
    is_verified: bool
    created_at: datetime

    comments: List[CommentResponse] = []
    
    class Config:
        from_attributes = True

class ReservationCreate(BaseModel):
    partner_name: str
    reservation_date: str
    reservation_time: str
    memo: Optional[str] = None

# 문서 상태 변경 (승인/반려) 요청
class StatusUpdate(BaseModel):
    status: str

# 커뮤니티 글 검증 마크 부여 요청
class PostVerifyUpdate(BaseModel):
    is_verified: bool