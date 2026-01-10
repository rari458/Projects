# app/main.py

import json
import shutil
import os
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer # 필수 라이브러리
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

# 토큰 인증을 위한 스킴 설정 (URL은 /token 엔드포인트를 가리킴)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

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
# 1. 인증 (로그인 & 내 정보 조회)
# ---------------------------------------------------------

@app.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # 1. 유저 인증 확인
    user = services.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 2. 토큰 생성
    access_token_expires = timedelta(minutes=services.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = services.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    # 3. 토큰과 함께 유저 정보 반환
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user_id": user.id,
        "user_name": user.full_name,
        "visa_type": user.visa_type,
        "is_admin": user.is_admin
    }

# [New] 토큰으로 내 정보 가져오기 API (프론트엔드 세션 복구용)
@app.get("/users/me", response_model=schemas.User)
def read_users_me(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # services.py에 추가한 get_user_by_token 함수 사용
    user = services.get_user_by_token(db, token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

# ---------------------------------------------------------
# 2. 회원가입 및 프로필 관리
# ---------------------------------------------------------

@app.post("/users/signup", response_model=schemas.User)
def create_user(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    existing_email = db.query(models.User).filter(models.User.email == user_data.email).first()
    existing_user = db.query(models.User).filter(models.User.username == user_data.username).first()
    
    if existing_email:
        raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다.")
    if existing_user:
        raise HTTPException(status_code=400, detail="이미 존재하는 아이디입니다.")
    
    is_admin_user = (user_data.username == "admin")

    new_user = models.User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=services.get_password_hash(user_data.password),
        is_admin=is_admin_user
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

@app.patch("/users/{user_id}/visa", response_model=schemas.User)
def update_user_profile(user_id: int, user_update: schemas.UserUpdate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user_update.visa_type is not None:
        db_user.visa_type = user_update.visa_type
    if user_update.nationality is not None:
        db_user.nationality = user_update.nationality
    if user_update.entry_date is not None:
        db_user.entry_date = user_update.entry_date
        
    db.commit()
    db.refresh(db_user)

    if user_update.visa_type:
        services.generate_roadmap(db, db_user) 

    return db_user

# ---------------------------------------------------------
# 3. 로드맵 조회 및 관리
# ---------------------------------------------------------
@app.get("/users/{user_id}/roadmap", response_model=schemas.RoadmapResponse)
def get_my_roadmap(user_id: int, db: Session = Depends(get_db)):
    roadmap = db.query(models.Roadmap).filter(models.Roadmap.user_id == user_id).first()
    
    if not roadmap:
         return {"id": 0, "title": "설정 필요", "steps": []}
         
    return roadmap

class StepUpdate(BaseModel):
    status: str

@app.patch("/roadmap-steps/{step_id}")
def update_step_status(step_id: int, request: StepUpdate, db: Session = Depends(get_db)):
    step = db.query(models.RoadmapStep).filter(models.RoadmapStep.id == step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="단계를 찾을 수 없습니다.")
    
    step.status = request.status 
    db.commit()
    return {"id": step.id, "status": step.status}

@app.post("/roadmap-steps/{step_id}/comments", response_model=schemas.StepCommentResponse)
def create_step_comment(step_id: int, comment: schemas.StepCommentCreate, user_id: int, db: Session = Depends(get_db)):
    step = db.query(models.RoadmapStep).filter(models.RoadmapStep.id == step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="단계를 찾을 수 없습니다.")
    
    new_comment = models.StepComment(
        step_id=step_id,
        author_id=user_id,
        content=comment.content,
        created_at=datetime.now()
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    return new_comment

# ---------------------------------------------------------
# 4. 문서 업로드 및 AI 분석
# ---------------------------------------------------------
@app.post("/users/{user_id}/documents", response_model=None)
def upload_document(
    user_id: int, 
    doc_type: str,
    step_id: Optional[int] = None,
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    try:
        # 파일명 안전하게 생성 (타임스탬프 정수형 변환)
        safe_filename = f"{int(datetime.now().timestamp())}_{file.filename}"
        file_location = os.path.join(UPLOAD_DIR, safe_filename)
        
        # 파일 저장
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
        
        # DB 기록
        new_doc = models.Document(
            user_id=user_id,
            step_id=step_id,
            doc_type=doc_type,
            s3_key=file_location,
            verification_status="REVIEW_NEEDED" if step_id else "UNVERIFIED"
        )
        db.add(new_doc)
        db.commit()
        db.refresh(new_doc)

        # 로드맵 단계 상태 업데이트 (대기 -> 검토중)
        if step_id:
            step = db.query(models.RoadmapStep).filter(models.RoadmapStep.id == step_id).first()
            if step and step.status == "대기":
                step.status = "검토중"
                db.commit()

        return {
            "id": new_doc.id,
            "filename": file.filename, 
            "saved_path": file_location,
            "status": new_doc.verification_status
        }
    except Exception as e:
        # 에러 발생 시 500 에러 반환
        raise HTTPException(status_code=500, detail=f"파일 업로드 실패: {str(e)}")

@app.post("/documents/{doc_id}/analyze")
def analyze_document(doc_id: int, user_id: int = 1, db: Session = Depends(get_db)): 
    document = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="문서 없음")
    
    services.log_action(db, document.user_id, "ANALYZE_DOC", doc_id)
    
    try:
        ai_result_text = services.analyze_document_with_ai(document.s3_key, document.doc_type)
        clean_json = ai_result_text.replace("```json", "").replace("```", "").strip()
        parsed_result = json.loads(clean_json)
        
        document.risk_analysis = clean_json
        document.verification_status = parsed_result.get("verification", "UNVERIFIED")
        
        expiry = parsed_result.get("expiry_date")
        if expiry:
            try:
                document.expiry_date = datetime.strptime(expiry, "%Y-%m-%d").date()
            except:
                pass

        db.commit()
        return {"status": "Analysis Completed", "result": parsed_result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"오류: {str(e)}")

# ---------------------------------------------------------
# 5. 파트너 비교 & 기관 찾기
# ---------------------------------------------------------
@app.get("/partners/{category}")
def get_partners(category: str):
    # 프론트엔드에서 요구하는 Rich Data 형식으로 변경
    return {
        "category": category,
        "comparison": {
            "self": {
                "title": "혼자 하기 (DIY)",
                "cost": 0 if category == "BANK" else 30000 if category == "VISA" else 0,
                "time": "4~5시간 (이동 포함)",
                "stress": "High (복잡함)",
                "success_rate": "85% (서류 미비 반려 위험)"
            },
            "expert": {
                "title": "파트너 위임 (Pro)",
                "cost": 50000 if category == "VISA" else 0,
                "time": "10분 (비대면)",
                "stress": "Zero",
                "success_rate": "99.9% (보장)",
                "partners": [
                    {"name": "김정수 행정사", "rating": 4.9, "badge": "CERTIFIED", "review_cnt": 128, "sla": "10분 내 응답"},
                    {"name": "Global Visa Lab", "rating": 4.7, "badge": "BEST PRICE", "review_cnt": 85, "sla": "1시간 내 응답"}
                ]
            }
        }
    }

@app.get("/agencies")
def get_agencies(category: str):
    agencies = []
    
    # ---------------------------------------------------------
    # 1. 연세대 (Sinchon) - 서대문구/마포구
    # ---------------------------------------------------------
    if category in ["BANK", "ALL"]:
        agencies.append({"id": 1, "name": "우리은행 연세금융센터", "category": "BANK", "lat": 37.5643, "lon": 126.9365, "address": "연세대학교 공학원 1층", "rating": 4.5})
        agencies.append({"id": 2, "name": "신한은행 신촌지점", "category": "BANK", "lat": 37.5552, "lon": 126.9369, "address": "서울 서대문구 신촌로 99", "rating": 4.2})
    
    if category in ["OFFICE", "ALL"]:
        agencies.append({"id": 3, "name": "서대문구청", "category": "OFFICE", "lat": 37.5791, "lon": 126.9368, "address": "서울 서대문구 연희로 248", "rating": 3.8})
        agencies.append({"id": 4, "name": "신촌동 주민센터", "category": "OFFICE", "lat": 37.5598, "lon": 126.9425, "address": "서울 서대문구 신촌역로 22-8", "rating": 4.0})
    
    if category in ["IMMIGRATION", "ALL"]:
        # 연세대 관할: 서울남부(목동)
        agencies.append({"id": 5, "name": "서울출입국·외국인청 (목동)", "category": "IMMIGRATION", "lat": 37.5195, "lon": 126.8679, "address": "서울 양천구 목동동로 151 (관할)", "rating": 2.5})

    # ---------------------------------------------------------
    # 2. 서울대 (Gwanak) - 관악구
    # ---------------------------------------------------------
    if category in ["BANK", "ALL"]:
        agencies.append({"id": 11, "name": "신한은행 서울대지점", "category": "BANK", "lat": 37.4593, "lon": 126.9535, "address": "서울대 학생회관 1층", "rating": 4.8})
        agencies.append({"id": 12, "name": "농협은행 서울대지점", "category": "BANK", "lat": 37.4645, "lon": 126.9550, "address": "서울대 행정관", "rating": 4.1})
    
    if category in ["OFFICE", "ALL"]:
        agencies.append({"id": 13, "name": "관악구청", "category": "OFFICE", "lat": 37.4784, "lon": 126.9516, "address": "서울 관악구 관악로 145", "rating": 4.3})
        agencies.append({"id": 14, "name": "낙성대동 주민센터", "category": "OFFICE", "lat": 37.4765, "lon": 126.9635, "address": "서울 관악구 남부순환로 1922", "rating": 3.9})

    # ---------------------------------------------------------
    # 3. 고려대 (Anam) - 성북구
    # ---------------------------------------------------------
    if category in ["BANK", "ALL"]:
        agencies.append({"id": 21, "name": "하나은행 고려대점", "category": "BANK", "lat": 37.5890, "lon": 127.0330, "address": "고려대 중앙광장", "rating": 4.6})
    
    if category in ["OFFICE", "ALL"]:
        agencies.append({"id": 23, "name": "성북구청", "category": "OFFICE", "lat": 37.5894, "lon": 127.0167, "address": "서울 성북구 보문로 168", "rating": 4.0})
    
    if category in ["IMMIGRATION", "ALL"]:
        # 고려대 관할: 세종로출장소
        agencies.append({"id": 25, "name": "세종로출장소 (종로)", "category": "IMMIGRATION", "lat": 37.5705, "lon": 126.9830, "address": "서울 종로구 종로 38 (관할)", "rating": 3.0})

    # ---------------------------------------------------------
    # 4. 한양대 (Seoul) - 성동구
    # ---------------------------------------------------------
    if category in ["BANK", "ALL"]:
        agencies.append({"id": 31, "name": "신한은행 한양대점", "category": "BANK", "lat": 37.5572, "lon": 127.0453, "address": "한양대 동문회관", "rating": 4.3})
    
    if category in ["OFFICE", "ALL"]:
        agencies.append({"id": 32, "name": "성동구청", "category": "OFFICE", "lat": 37.5635, "lon": 127.0365, "address": "서울 성동구 고산자로 270", "rating": 4.1})

    return agencies

# ---------------------------------------------------------
# [UPGRADE] 파트너 비교 데이터 (기획서 SLA/인증 반영)
# ---------------------------------------------------------
@app.get("/partners/{category}")
def get_partner_comparison(category: str):
    # 실제로는 DB에서 가져와야 함
    return {
        "category": category,
        "comparison": {
            "self": {
                "title": "혼자 하기 (DIY)",
                "cost": 0 if category == "BANK" else 30000 if category == "VISA" else 0,
                "time": "4~5시간 (이동 포함)",
                "stress": "High (복잡함)",
                "success_rate": "85% (서류 미비 반려 위험)"
            },
            "expert": {
                "title": "파트너 위임 (Pro)",
                "cost": 50000 if category == "VISA" else 0, # 부동산/은행은 수수료 구조가 다름
                "time": "10분 (비대면)",
                "stress": "Zero",
                "success_rate": "99.9% (보장)",
                "partners": [
                    {"name": "김정수 행정사", "rating": 4.9, "badge": "CERTIFIED", "review_cnt": 128, "sla": "10분 내 응답"},
                    {"name": "Global Visa Lab", "rating": 4.7, "badge": "BEST PRICE", "review_cnt": 85, "sla": "1시간 내 응답"}
                ]
            }
        }
    }

# ---------------------------------------------------------
# 6. AI 챗봇 & 커뮤니티
# ---------------------------------------------------------
class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
def chat_with_ai(request: ChatRequest):
    response = services.get_chat_response(request.message)
    return {"reply": response}

@app.post("/community/posts", response_model=schemas.PostResponse)
def create_post(post: schemas.PostCreate, user_id: int, db: Session = Depends(get_db)):
    is_admin = (user_id == 1)

    new_post = models.BoardPost(
        title=post.title,
        content=post.content, 
        author_id=user_id,
        visa_type=post.visa_type,
        category=post.category,
        result_tag=post.result_tag,
        is_verified=is_admin
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post

@app.get("/community/posts", response_model=List[schemas.PostResponse])
def get_posts(
    visa_filter: str = None, 
    category: str = None,     # [NEW] 카테고리 필터
    verified_only: bool = False, # [NEW] 검증글 필터
    db: Session = Depends(get_db)
):
    query = db.query(models.BoardPost)
    
    if visa_filter and visa_filter != "ALL":
        query = query.filter(models.BoardPost.visa_type == visa_filter)
        
    if category:
        query = query.filter(models.BoardPost.category == category)
        
    if verified_only:
        query = query.filter(models.BoardPost.is_verified == True)
        
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

class PostUpdate(BaseModel):
    title: str
    content: str

@app.put("/community/posts/{post_id}")
def update_post(post_id: int, post_update: PostUpdate, user_id: int, db: Session = Depends(get_db)):
    post = db.query(models.BoardPost).filter(models.BoardPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    if post.author_id != user_id:
        raise HTTPException(status_code=403, detail="수정 권한이 없습니다.")
    
    post.title = post_update.title
    post.content = post_update.content
    db.commit()
    return {"status": "updated", "id": post.id}

@app.delete("/community/posts/{post_id}")
def delete_post(post_id: int, user_id: int, db: Session = Depends(get_db)):
    post = db.query(models.BoardPost).filter(models.BoardPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    if post.author_id != user_id:
        raise HTTPException(status_code=403, detail="삭제 권한이 없습니다.")
    
    db.query(models.BoardComment).filter(models.BoardComment.post_id == post_id).delete()
    db.delete(post)
    db.commit()
    return {"status": "deleted", "id": post_id}

@app.patch("/checklist-items/{item_id}")
def update_checklist_item(item_id: int, update: schemas.ChecklistUpdate, db: Session = Depends(get_db)):
    item = db.query(models.StepChecklist).filter(models.StepChecklist.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item.is_checked = update.is_checked
    db.commit()
    return {"id": item.id, "is_checked": item.is_checked}

# ---------------------------------------------------------
# 7. 감사 로그 & 알림 (Trust System)
# ---------------------------------------------------------
@app.get("/users/{user_id}/audit-logs")
def get_audit_logs(user_id: int, db: Session = Depends(get_db)):
    # 최신순으로 10개만 가져오기
    logs = db.query(models.AuditLog)\
             .filter(models.AuditLog.user_id == user_id)\
             .order_by(models.AuditLog.timestamp.desc())\
             .limit(10).all()
    return logs

@app.post("/reservations")
def create_reservation(res: schemas.ReservationCreate, user_id: int, db: Session = Depends(get_db)):
    new_res = models.Reservation(
        user_id=user_id,
        partner_name=res.partner_name,
        reservation_date=res.reservation_date,
        reservation_time=res.reservation_time,
        memo=res.memo
    )
    db.add(new_res)
    db.commit()
    return {"status": "success", "msg": "예약이 확정되었습니다."}

@app.get("/users/{user_id}/reservations")
def get_reservations(user_id: int, db: Session = Depends(get_db)):
    return db.query(models.Reservation).filter(models.Reservation.user_id == user_id).all()

class StatusUpdate(BaseModel):
    status: str

@app.patch("/documents/{doc_id}/status")
def update_document_status(doc_id: int, update: StatusUpdate, db: Session = Depends(get_db)):
    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not doc: raise HTTPException(status_code=404, detail="Not Found")
    doc.verification_status = update.status
    db.commit()
    return {"status": "ok"}

class PostVerifyUpdate(BaseModel):
    is_verified: bool

@app.patch("/community/posts/{post_id}/verify")
def verify_community_post(post_id: int, update: PostVerifyUpdate, db: Session = Depends(get_db)):
    post = db.query(models.BoardPost).filter(models.BoardPost.id == post_id).first()
    if not post: raise HTTPException(status_code=404, detail="Not Found")
    post.is_verified = update.is_verified
    db.commit()
    return {"status": "ok"}

@app.get("/admin/pending-documents")
def get_pending_documents(db: Session = Depends(get_db)):
    return db.query(models.Document).filter(models.Document.verification_status == "REVIEW_NEEDED").all()

@app.get("/admin/reservations")
def get_all_reservations(db: Session = Depends(get_db)):
    return db.query(models.Reservation).order_by(models.Reservation.created_at.desc()).all()

# [NEW] 내 문서 목록 조회 (문서 지갑용)
@app.get("/users/{user_id}/documents", response_model=List[schemas.DocumentResponse])
def get_user_documents(user_id: int, db: Session = Depends(get_db)):
    return db.query(models.Document).filter(models.Document.user_id == user_id).order_by(models.Document.uploaded_at.desc()).all()