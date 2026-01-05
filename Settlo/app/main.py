# app/main.py (최종 수정 버전)

import json
import shutil
import os
from datetime import datetime
from typing import List

from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import engine, SessionLocal
from app import models, schemas, services

# 앱 시작 시 업로드 폴더 자동 생성
UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# DB 테이블 생성
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Settlo API")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Settlo API Running"}

# ---------------------------------------------------------
# 1. 회원가입 및 로드맵
# ---------------------------------------------------------
@app.post("/users/signup", response_model=schemas.UserResponse)
def create_user(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다.")

    new_user = models.User(
        email=user_data.email,
        hashed_password=user_data.password + "_fakehash" 
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    new_profile = models.UserProfile(
        user_id=new_user.id,
        full_name=user_data.full_name,
        nationality=user_data.nationality,
        visa_type=user_data.visa_type,
        university=user_data.university,
        entry_date=user_data.entry_date
    )
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)

    # 로드맵 자동 생성
    services.generate_roadmap(db, new_user, new_profile)

    return {
        "id": new_user.id,
        "email": new_user.email,
        "full_name": new_profile.full_name
    }

@app.get("/users/{user_id}/roadmap", response_model=schemas.RoadmapResponse)
def get_my_roadmap(user_id: int, db: Session = Depends(get_db)):
    roadmap = db.query(models.Roadmap).filter(models.Roadmap.user_id == user_id).first()
    if not roadmap:
        raise HTTPException(status_code=404, detail="로드맵을 찾을 수 없습니다.")
    return roadmap

# [수정] 상태 업데이트 모델
class StepUpdate(BaseModel):
    status: str  # "대기", "검토중", "완료" 등 한글 Enum 값

@app.patch("/roadmap-steps/{step_id}")
def update_step_status(step_id: int, request: StepUpdate, db: Session = Depends(get_db)):
    step = db.query(models.RoadmapStep).filter(models.RoadmapStep.id == step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="단계를 찾을 수 없습니다.")
    
    # [핵심 수정] 전달받은 상태 값을 그대로 적용 (단순 COMPLETED 체크 X)
    # models.StepStatus Enum에 없는 값이면 에러가 날 수 있으나, Frontend에서 맞춰서 보냄
    step.status = request.status 
        
    db.commit()
    return {"id": step.id, "status": step.status}

class VisaUpdate(BaseModel):
    visa_type: str

@app.patch("/users/{user_id}/visa")
def update_user_visa(user_id: int, request: VisaUpdate, db: Session = Depends(get_db)):
    updated_profile = services.update_visa_and_roadmap(db, user_id, request.visa_type)
    if not updated_profile:
        raise HTTPException(status_code=404, detail="유저를 찾을 수 없습니다.")
    return {"status": "updated", "new_visa": updated_profile.visa_type}

# [신규] 로드맵 단계별 질문/댓글 달기 (Q&A)
@app.post("/roadmap-steps/{step_id}/comments", response_model=schemas.StepCommentResponse)
def create_step_comment(step_id: int, comment: schemas.StepCommentCreate, user_id: int, db: Session = Depends(get_db)):
    # 1. 단계 존재 확인
    step = db.query(models.RoadmapStep).filter(models.RoadmapStep.id == step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="단계를 찾을 수 없습니다.")
    
    # 2. 댓글 저장
    new_comment = models.StepComment(
        step_id=step_id,
        author_id=user_id,
        content=comment.content
    )
    db.add(new_comment)
    
    # 3. (옵션) 질문이 달리면 상태를 '자료요청'이나 '검토중'으로 자동 변경할 수도 있음
    # step.status = models.StepStatus.REQUEST_DATA 
    
    db.commit()
    db.refresh(new_comment)
    return new_comment

# ---------------------------------------------------------
# 2. 문서 업로드 및 AI 분석
# ---------------------------------------------------------
@app.post("/users/{user_id}/documents", response_model=None)
def upload_document(
    user_id: int, 
    doc_type: str, 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    file_location = f"{UPLOAD_DIR}/{datetime.now().timestamp()}_{file.filename}"
    
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
    
    new_doc = models.Document(
        user_id=user_id,
        doc_type=doc_type,
        s3_key=file_location,
        verification_status=models.DocStatus.UNVERIFIED
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    
    return {"filename": file.filename, "saved_path": file_location, "status": "Uploaded"}

# ---------------------------------------------------------
# [신규] 파트너 비교 데이터 제공 API
# ---------------------------------------------------------
@app.get("/partners/{category}")
def get_partners(category: str):
    """
    해당 카테고리(VISA, HOUSING 등)의 '직접 진행 vs 전문가 위임' 비교 데이터와 파트너 리스트 반환
    """
    # 실제로는 DB에서 가져와야 하지만, 데모용 Mock Data 사용
    comparison = {
        "self": {"cost": 30000, "time": "5일 (방문 2회)", "difficulty": "높음"},
        "expert": {"cost": 150000, "time": "1일 (방문 0회)", "difficulty": "낮음"}
    }
    
    partners = [
        {"id": 1, "name": "김정수 행정사", "rating": 4.9, "review_count": 120, "price": 150000},
        {"id": 2, "name": "Global Visa Center", "rating": 4.7, "review_count": 85, "price": 140000},
    ]
    
    if category == "HOUSING":
        comparison = {
            "self": {"cost": 0, "time": "14일 (발품 10회)", "difficulty": "매우 높음"},
            "expert": {"cost": 300000, "time": "3일 (추천 3개)", "difficulty": "낮음"}
        }
        partners = [
            {"id": 3, "name": "외국인 친화 부동산", "rating": 4.8, "price": "법정 수수료"},
            {"id": 4, "name": "Campus Home", "rating": 4.5, "price": "수수료 10% 할인"}
        ]

    return {"comparison": comparison, "partners": partners}

# ---------------------------------------------------------
# [수정] 문서 분석 API (만료일 저장 & 로그 기록)
# ---------------------------------------------------------
@app.post("/documents/{doc_id}/analyze")
def analyze_document(doc_id: int, user_id: int = 1, db: Session = Depends(get_db)): 
    # user_id는 데모용 기본값 1, 실제론 토큰에서 추출
    
    document = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="문서 없음")
    
    # [Log] 분석 시도 기록
    services.log_action(db, document.user_id, "ANALYZE_DOC", doc_id)
    
    try:
        # AI 분석 호출
        ai_result_text = services.analyze_document_with_ai(document.s3_key, document.doc_type)
        
        # JSON 텍스트 파싱 (Expiry Date 추출을 위해)
        # Gemini가 가끔 ```json ... ``` 형태로 줄 때가 있어 처리 필요
        clean_json = ai_result_text.replace("```json", "").replace("```", "").strip()
        parsed_result = json.loads(clean_json)
        
        # DB 업데이트
        document.risk_analysis = clean_json # 원본 텍스트 저장
        document.verification_status = parsed_result.get("verification", "UNVERIFIED")
        
        # [핵심] 만료일 저장
        expiry = parsed_result.get("expiry_date")
        if expiry:
            try:
                document.expiry_date = datetime.strptime(expiry, "%Y-%m-%d").date()
            except:
                pass # 날짜 변환 실패 시 무시

        db.commit()
        return {"status": "Analysis Completed", "result": parsed_result}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"오류: {str(e)}")

# ---------------------------------------------------------
# 3. AI 챗봇
# ---------------------------------------------------------
class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
def chat_with_ai(request: ChatRequest):
    response = services.get_chat_response(request.message)
    return {"reply": response}


# ---------------------------------------------------------
# 4. 커뮤니티
# ---------------------------------------------------------
@app.post("/community/posts", response_model=schemas.PostResponse)
def create_post(post: schemas.PostCreate, user_id: int, db: Session = Depends(get_db)):
    new_post = models.BoardPost(
        title=post.title, 
        content=post.content, 
        author_id=user_id,
        visa_type=post.visa_type,
        result_tag=post.result_tag
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post

@app.get("/community/posts", response_model=List[schemas.PostResponse])
def get_posts(visa_filter: str = None, db: Session = Depends(get_db)):
    """
    visa_filter가 있으면 해당 비자 글만, 없으면 전체 글 조회
    """
    query = db.query(models.BoardPost)
    
    if visa_filter and visa_filter != "ALL":
        query = query.filter(models.BoardPost.visa_type == visa_filter)
        
    return query.order_by(models.BoardPost.id.desc()).all()

@app.post("/community/posts/{post_id}/comments", response_model=schemas.CommentResponse)
def create_comment(post_id: int, comment: schemas.CommentCreate, user_id: int, db: Session = Depends(get_db)):
    new_comment = models.BoardComment(
        content=comment.content, post_id=post_id, author_id=user_id
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    return new_comment

# --- [추가] 게시글 수정용 데이터 모델 ---
class PostUpdate(BaseModel):
    title: str
    content: str

# 4. 게시글 수정 (PUT)
@app.put("/community/posts/{post_id}")
def update_post(post_id: int, post_update: PostUpdate, user_id: int, db: Session = Depends(get_db)):
    # 게시글 찾기
    post = db.query(models.BoardPost).filter(models.BoardPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    
    # 작성자 확인 (본인만 수정 가능)
    if post.author_id != user_id:
        raise HTTPException(status_code=403, detail="수정 권한이 없습니다.")
    
    # 내용 업데이트
    post.title = post_update.title
    post.content = post_update.content
    db.commit()
    return {"status": "updated", "id": post.id}

# 5. 게시글 삭제 (DELETE)
@app.delete("/community/posts/{post_id}")
def delete_post(post_id: int, user_id: int, db: Session = Depends(get_db)):
    post = db.query(models.BoardPost).filter(models.BoardPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    
    # 작성자 확인
    if post.author_id != user_id:
        raise HTTPException(status_code=403, detail="삭제 권한이 없습니다.")
    
    # 삭제 실행
    # (주의: 실제 서비스에선 댓글도 같이 지우거나(cascade), '삭제됨' 상태로 변경하는 게 안전함)
    # 여기서는 간단히 해당 글에 달린 댓글 먼저 지우고 글을 지웁니다.
    db.query(models.BoardComment).filter(models.BoardComment.post_id == post_id).delete()
    db.delete(post)
    db.commit()
    
    return {"status": "deleted", "id": post_id}

# ---------------------------------------------------------
# [신규] 5. 기관 리스트 (지도 서비스)
# ---------------------------------------------------------
@app.get("/agencies")
def get_agencies(category: str = "ALL"):
    """
    카테고리별(BANK, OFFICE, IMMIGRATION) 주변 기관 좌표 반환 (Mock Data)
    """
    # 기준: 서울시청 좌표 (37.5665, 126.9780)
    base_lat = 37.5665
    base_lon = 126.9780
    
    agencies = []
    
    # 1. 은행 (BANK)
    if category in ["ALL", "BANK"]:
        agencies.append({"name": "우리은행 본점", "lat": base_lat + 0.002, "lon": base_lon + 0.001, "type": "BANK", "address": "서울 중구 소공로"})
        agencies.append({"name": "신한은행 시청역점", "lat": base_lat - 0.002, "lon": base_lon + 0.002, "type": "BANK", "address": "서울 중구 세종대로"})
        agencies.append({"name": "하나은행 광화문점", "lat": base_lat + 0.005, "lon": base_lon - 0.003, "type": "BANK", "address": "서울 종로구"})

    # 2. 관공서 (OFFICE - 구청, 주민센터)
    if category in ["ALL", "OFFICE"]:
        agencies.append({"name": "서울시청 민원실", "lat": base_lat, "lon": base_lon, "type": "OFFICE", "address": "서울 중구 세종대로 110"})
        agencies.append({"name": "종로구청", "lat": base_lat + 0.012, "lon": base_lon + 0.005, "type": "OFFICE", "address": "서울 종로구 삼봉로"})

    # 3. 출입국사무소 (IMMIGRATION)
    if category in ["ALL", "IMMIGRATION"]:
        # (거리가 좀 멀지만 지도 확인용으로 추가)
        agencies.append({"name": "서울출입국·외국인청 (목동)", "lat": 37.517, "lon": 126.867, "type": "IMMIGRATION", "address": "서울 양천구 목동동로"})
        agencies.append({"name": "세종로출장소", "lat": 37.570, "lon": 126.980, "type": "IMMIGRATION", "address": "서울 종로구 종로1가"})

    return agencies