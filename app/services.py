from sqlalchemy.orm import Session
from datetime import timedelta, datetime, date
import os
import google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image
from app import models
import bcrypt  # [변경] passlib 대신 bcrypt 직접 사용
from jose import jwt, JWTError
import mimetypes
import json

# 환경 변수 로드
load_dotenv()

# ---------------------------------------------------------
# [New] 보안 및 인증 설정 (비밀번호 해시 & JWT)
# ---------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key_here") 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# [수정] bcrypt 직접 사용하여 비밀번호 검증
def verify_password(plain_password, hashed_password):
    # DB에 저장된 해시(String)를 Bytes로 변환해야 함
    return bcrypt.checkpw(
        plain_password.encode('utf-8'), 
        hashed_password.encode('utf-8')
    )

# [수정] bcrypt 직접 사용하여 비밀번호 해싱
def get_password_hash(password):
    # 비밀번호를 Bytes로 변환 후 해싱 -> 다시 String으로 변환하여 저장
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_bytes.decode('utf-8')

# 로그인 인증 처리
def authenticate_user(db: Session, username: str, password: str):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

# 액세스 토큰 생성
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Gemini 설정
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# ---------------------------------------------------------
# [공통 내부 함수] 로드맵 단계 생성 (카테고리 매핑 수정됨)
# ---------------------------------------------------------
def _create_roadmap_steps(db: Session, roadmap_id: int, visa_type_str: str, entry_date: date):
    if not entry_date:
        entry_date = date.today()

    steps_data = []

    # 1. [통신] 휴대폰 개통 (SIM) - 가장 시급
    steps_data.append({
        "info": {
            "title": "휴대폰 개통 (유심/eSIM)",
            "category": "SIM", # 프론트엔드 '통신' 버튼 대응
            "description": "본인 인증을 위해 필수. 알뜰폰 또는 메이저 통신사 가입.",
            "order": 1,
            "deadline": entry_date + timedelta(days=2)
        },
        "items": ["여권", "신용카드(결제용)", "입국 확인증"]
    })

    # 2. [행정] 입국 신고 (VISA로 통합 -> 행정 버튼에서 보임)
    steps_data.append({
        "info": {
            "title": "입국 신고 및 자가격리 확인",
            "category": "VISA", # 'ENTRY' 대신 'VISA'(행정)로 통합
            "description": "공항 도착 후 검역 절차 확인. 짐 찾기 전 Q-Code 준비.",
            "order": 2,
            "deadline": entry_date + timedelta(days=1)
        },
        "items": ["Q-Code 발급", "입국심사 확인증", "세관신고서"]
    })
    
    # 3. [주거] 부동산 계약 (HOUSING)
    steps_data.append({
        "info": {
            "title": "부동산 임대차 계약 (주거 확보)",
            "category": "HOUSING",
            "description": "학교 근처 원룸/고시텔 계약. 보증금 보호 조항 확인 필수.",
            "order": 3,
            "deadline": entry_date + timedelta(days=7)
        },
        "items": ["여권 사본", "보증금 예산 확보", "표준임대차계약서 확인", "등기부등본 열람"]
    })

    # 4. [행정] 비자/등록증 (VISA)
    visa_str = str(visa_type_str)
    if "D-2" in visa_str:
        steps_data.append({
            "info": {
                "title": "외국인 등록증 신청 (D-2)",
                "category": "VISA",
                "description": "입국 후 90일 이내 필수. 하이코리아 방문 예약 필요.",
                "order": 4,
                "deadline": entry_date + timedelta(days=90)
            },
            "items": ["통합신청서", "여권 원본 및 사본", "재학증명서", "거주숙소제공확인서", "수수료(3만원)"]
        })
    elif "D-4" in visa_str:
        steps_data.append({
            "info": {
                "title": "외국인 등록증 신청 (D-4)",
                "category": "VISA",
                "description": "어학연수생 필수 등록. 출석률 증빙 필요 가능성 있음.",
                "order": 4,
                "deadline": entry_date + timedelta(days=90)
            },
            "items": ["통합신청서", "여권", "어학당 재학증명서", "거주지 입증서류", "수수료"]
        })

    # 5. [금융] 은행 (BANK)
    steps_data.append({
        "info": {
            "title": "은행 계좌 개설 및 카드 발급",
            "category": "BANK",
            "description": "외국인등록증 수령 후 방문 권장. (여권만으로는 한도제한 계좌)",
            "order": 5,
            "deadline": entry_date + timedelta(days=14)
        },
        "items": ["외국인등록증", "여권", "재학증명서(용도증빙)", "현금(초기 입금용)"]
    })

    # 6. [학교] 수강신청 (SCHOOL) - 추가됨
    steps_data.append({
        "info": {
            "title": "수강신청 및 학생증 발급",
            "category": "SCHOOL", # 프론트엔드 '학교' 버튼 대응
            "description": "학교 포털 가입 및 필수 교양 과목 신청. 학생증 사진 준비.",
            "order": 6,
            "deadline": entry_date + timedelta(days=10)
        },
        "items": ["학번 조회", "수강편람 확인", "증명사진(jpg)"]
    })

    # DB 저장 로직 (기존과 동일)
    for step_dict in steps_data:
        info = step_dict["info"]
        new_step = models.RoadmapStep(
            roadmap_id=roadmap_id,
            title=info["title"],
            category=info["category"],
            description=info["description"],
            order_index=info["order"],
            deadline=info["deadline"],
            status="대기"
        )
        db.add(new_step)
        db.flush()

        for item_text in step_dict["items"]:
            new_checklist = models.StepChecklist(
                step_id=new_step.id,
                item_content=item_text,
                is_checked=False
            )
            db.add(new_checklist)
    
    db.commit()

# ---------------------------------------------------------
# 1. 로드맵 생성 로직
# ---------------------------------------------------------
# app/services.py 내부 generate_roadmap 함수 (수정본)

def generate_roadmap(db: Session, user: models.User):
    # 1. 기존 로드맵이 있는지 확인
    existing_roadmap = db.query(models.Roadmap).filter(models.Roadmap.user_id == user.id).first()
    
    if existing_roadmap:
        # [핵심 수정]
        # 기존 코드처럼 db.query(models.RoadmapStep).delete()를 직접 호출하면 
        # 체크리스트(Checklist) 같은 하위 데이터가 제대로 안 지워질 수 있습니다.
        # 
        # models.py에서 cascade="all, delete-orphan"을 설정했으므로,
        # 최상위 부모인 'existing_roadmap' 객체 하나만 지우면
        # 연결된 Steps와 Checklist들이 연쇄적으로 깔끔하게 삭제됩니다.
        db.delete(existing_roadmap)
        db.commit()

    # 2. 새 로드맵 생성
    new_roadmap = models.Roadmap(
        user_id=user.id,
        title=f"{user.full_name}님의 {user.visa_type} 정착 워크플로우"
    )
    db.add(new_roadmap)
    db.commit()
    db.refresh(new_roadmap)

    # 3. 단계 및 체크리스트 생성 (내부 함수 호출)
    _create_roadmap_steps(db, new_roadmap.id, user.visa_type, user.entry_date)

    return new_roadmap

# ---------------------------------------------------------
# [수정] AI 문서 분석 로직
# ---------------------------------------------------------
def analyze_document_with_ai(file_path: str, doc_type: str):
    if not GOOGLE_API_KEY:
        return '{"summary": "API 키 없음", "risk_factors": [], "verification": "FAILED", "expiry_date": null}'

    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # 1. 파일 형식(MIME Type) 확인
        mime_type, _ = mimetypes.guess_type(file_path)
        
        content_part = None
        
        # 2. PDF일 경우: Gemini 전용 업로더 사용
        if mime_type == "application/pdf":
            # 파일을 Google 서버에 임시 업로드 (분석용)
            uploaded_file = genai.upload_file(file_path, mime_type=mime_type)
            content_part = uploaded_file
            
        # 3. 이미지일 경우: 기존 방식 사용
        else:
            content_part = Image.open(file_path)

        # ---------------------------------------------------------
        # 프롬프트 설정 (기존과 동일)
        # ---------------------------------------------------------
        if doc_type in ["PASSPORT", "ARC"]:
            prompt = """
            당신은 출입국 행정 전문가입니다. 이 신분증 이미지를 분석하여 JSON으로만 답하세요.
            {
                "summary": "문서 종류 및 이름 요약 (한국어)",
                "verification": "PASSED(정상) 또는 REVIEW_NEEDED(흐릿함/훼손)",
                "expiry_date": "YYYY-MM-DD (만료일 추출, 없으면 null)",
                "risk_factors": [] 
            }
            """
        elif doc_type == "CONTRACT":
            prompt = """
            당신은 한국 법률 전문가입니다. 이 계약서(임대차 또는 근로)를 분석하여 유학생에게 불리한 '독소 조항'을 찾아내세요.
            반드시 아래 JSON 형식으로만 응답하세요. (마크다운 없이)
            {
                "summary": "계약 핵심 요약 (보증금/월세 또는 시급/근무지 등 2줄 요약)",
                "risk_score": "0~100 사이 숫자 (높을수록 위험)",
                "risk_factors": [
                    {
                        "clause": "문제가 되는 조항 원문",
                        "reason": "위험한 이유 (초보자도 알기 쉽게 설명)",
                        "severity": "HIGH 또는 MID",
                        "suggestion": "집주인/고용주에게 요청할 정중한 수정 제안 멘트 (예: '표준임대차계약서에 따라 이 부분은 삭제해 주실 수 있나요?')"
                    }
                ],
                "safe_clauses": ["유리하거나 표준적인 조항 2~3개 요약"],
                "verification": "REVIEW_NEEDED"
            }
            """
        else:
            prompt = "이 문서를 요약해줘. JSON 포맷: {summary, risk_factors:[]}"

        generation_config = genai.types.GenerationConfig(temperature=0.0)

        # 4. 분석 요청 (이미지/PDF 객체 전달)
        response = model.generate_content(
            [prompt, content_part],
            generation_config=generation_config
        )
        return response.text

    except Exception as e:
        return f'{{"error": "분석 중 오류 발생: {str(e)}"}}'

# ---------------------------------------------------------
# 3. AI 챗봇
# ---------------------------------------------------------
def get_chat_response(user_message: str):
    if not GOOGLE_API_KEY:
        return {"reply": "API 키가 설정되지 않았습니다.", "action": None}

    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # 시스템 프롬프트: 답변과 행동(Action)을 같이 달라고 지시
        system_instruction = """
        당신은 'Settlo Mate'입니다. 외국인 유학생의 정착을 돕는 AI 컨시어지입니다.
        사용자의 질문을 분석하여 한국어로 친절하게 답변하고, 필요한 경우 앱 내 기능을 연결할 수 있는 'action' 코드를 반환하세요.
        
        반드시 아래 **JSON 형식**으로만 응답하세요. (마크다운 없이)
        
        {
            "reply": "사용자에게 할 답변 (이모지 포함, 3문장 내외)",
            "action": "ACTION_CODE"
        }
        
        [ACTION_CODE 목록]
        - "FIND_HOUSE": 집 구하기, 원룸, 고시텔, 보증금 관련 질문 시
        - "VISA_HELP": 비자 변경, 연장, 행정사, 외국인등록증 관련 질문 시
        - "CHECK_ROADMAP": 절차, 순서, 뭐부터 해야해? 관련 질문 시
        - "NONE": 위 경우에 해당하지 않는 일반적인 대화 (맛집, 인사 등)
        """
        
        response = model.generate_content(f"{system_instruction}\n\n사용자 질문: {user_message}")
        
        # JSON 파싱 (Gemini가 가끔 ```json ... ``` 이렇게 줄 때가 있어서 처리)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        
        try:
            return json.loads(clean_text)
        except json.JSONDecodeError:
            # 파싱 실패 시 텍스트만 리턴
            return {"reply": response.text, "action": "NONE"}
            
    except Exception as e:
        return {"reply": f"오류가 발생했습니다: {str(e)}", "action": "NONE"}
    
# ---------------------------------------------------------
# [신규] 감사 로그 (Audit Log) 기록
# ---------------------------------------------------------
def log_action(db: Session, user_id: int, action: str, target_id: int = 0):
    new_log = models.AuditLog(
        user_id=user_id,
        action=action,
        target_id=target_id
    )
    db.add(new_log)
    db.commit()

# app/services.py 맨 아래에 추가

def get_user_by_token(db: Session, token: str):
    """
    토큰을 해독해서 DB의 유저 정보를 가져오는 함수
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        
        # username으로 유저 찾기
        return db.query(models.User).filter(models.User.username == username).first()
    except JWTError:
        return None