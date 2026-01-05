# app/services.py (최종 수정 버전)

from sqlalchemy.orm import Session
from datetime import timedelta, date
import os
import google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image
from app import models

# 환경 변수 로드
load_dotenv()

# Gemini 설정
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# ---------------------------------------------------------
# [공통 내부 함수] 로드맵 단계 생성 (중복 제거용)
# ---------------------------------------------------------
def _create_roadmap_steps(db: Session, roadmap_id: int, visa_type_str: str, entry_date: date):
    """
    로드맵 ID와 조건을 받아 실제 단계(Step) 데이터를 DB에 생성하는 함수
    """
    steps_data = []

    # [1단계: 입국 및 주거] - 공통
    steps_data.append({
        "title": "입국 신고 및 자가격리 확인",
        "category": "ENTRY",
        "description": "공항 도착 후 검역 절차 확인 (유학생 전용 라인 이용)",
        "order": 1,
        "deadline": entry_date + timedelta(days=1)
    })
    
    # [2단계: 주거]
    steps_data.append({
        "title": "부동산 임대차 계약 (주거 확보)",
        "category": "HOUSING",
        "description": "기숙사가 아닌 경우 외부 숙소 계약 필요. (전문가 검토 권장)",
        "order": 2,
        "deadline": entry_date + timedelta(days=7)
    })

    # [3단계: 비자/행정] - ★ 조건 분기
    # Enum 객체든 문자열이든 안전하게 문자열로 변환하여 비교
    visa_str = str(visa_type_str) 
    
    if "D-2" in visa_str: # D-2 포함 여부로 확인
        steps_data.append({
            "title": "외국인 등록증 신청 (D-2)",
            "category": "VISA",
            "description": "90일 이내 필수. 재학증명서, 거주지 입증서류 준비.",
            "order": 3,
            "deadline": entry_date + timedelta(days=90)
        })
    elif "D-4" in visa_str:
        steps_data.append({
            "title": "외국인 등록증 신청 (D-4)",
            "category": "VISA",
            "description": "어학당 재학증명서 및 '출석 확인서' 필수 지참.",
            "order": 3,
            "deadline": entry_date + timedelta(days=90)
        })

    # [4단계: 금융] - 공통
    steps_data.append({
        "title": "은행 계좌 개설 및 카드 발급",
        "category": "BANK",
        "description": "여권+외국인등록증 지참. (최근 3개월 통신비 고지서 지참 시 한도 상향 가능)",
        "order": 4,
        "deadline": entry_date + timedelta(days=14)
    })

    # DB 저장
    for step in steps_data:
        new_step = models.RoadmapStep(
            roadmap_id=roadmap_id,
            title=step["title"],
            category=step["category"],
            description=step["description"],
            order_index=step["order"],
            deadline=step["deadline"],
            status=models.StepStatus.WAITING # 초기 상태: 대기
        )
        db.add(new_step)
    
    db.commit()


# ---------------------------------------------------------
# 1. 로드맵 생성 로직 (회원가입 시 사용)
# ---------------------------------------------------------
def generate_roadmap(db: Session, user: models.User, profile: models.UserProfile):
    # 1. 로드맵 객체 생성
    new_roadmap = models.Roadmap(
        user_id=user.id,
        title=f"{profile.full_name}님의 {profile.visa_type} 정착 워크플로우"
    )
    db.add(new_roadmap)
    db.commit()
    db.refresh(new_roadmap)

    # 2. 단계 생성 (공통 함수 호출)
    _create_roadmap_steps(db, new_roadmap.id, profile.visa_type, profile.entry_date)

    return new_roadmap


def update_visa_and_roadmap(db: Session, user_id: int, new_visa_type: str):
    # 1. 프로필 업데이트
    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == user_id).first()
    if not profile:
        return None
    
    # 모델 Enum에 맞춰 값 업데이트 (문자열이 들어와도 SQLAlchemy가 처리하거나 Enum 값으로 변환)
    profile.visa_type = new_visa_type
    db.commit()

    # 2. 기존 로드맵 단계 삭제 (초기화)
    roadmap = db.query(models.Roadmap).filter(models.Roadmap.user_id == user_id).first()
    if roadmap:
        db.query(models.RoadmapStep).filter(models.RoadmapStep.roadmap_id == roadmap.id).delete()
        db.commit()
        
        # 3. 로드맵 단계 재생성 (공통 함수 호출)
        _create_roadmap_steps(db, roadmap.id, new_visa_type, profile.entry_date)
        
    return profile


# ---------------------------------------------------------
# [수정] AI 문서 분석 로직 (만료일 추출 추가)
# ---------------------------------------------------------
def analyze_document_with_ai(file_path: str, doc_type: str):
    if not GOOGLE_API_KEY:
        return {
            "summary": "API 키 없음", "risk_factors": [], "verification": "FAILED", "expiry_date": None
        }

    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        img = Image.open(file_path)

        prompt = f"""
        당신은 출입국 행정 전문가입니다. 이 '{doc_type}' 이미지를 분석하여 JSON으로만 답하세요.
        
        1. summary: 핵심 내용 요약 (한국어, 2줄)
        2. risk_factors: 주의사항 리스트 (한국어)
        3. verification: 'PASSED' (정상) 또는 'REVIEW_NEEDED' (흐릿/의심)
        4. expiry_date: 문서의 만료일 또는 유효기간을 'YYYY-MM-DD' 형식으로 추출. (없으면 null)
        """

        response = model.generate_content([prompt, img])
        # 마크다운 ```json 제거 등 파싱 처리는 클라이언트나 main.py에서 할 수도 있지만, 
        # 여기서는 텍스트 그대로 리턴
        return response.text

    except Exception as e:
        return f"분석 실패: {str(e)}"

# ---------------------------------------------------------
# 3. AI 챗봇 (Settlo Mate)
# ---------------------------------------------------------
def get_chat_response(user_message: str):
    if not GOOGLE_API_KEY:
        return "죄송합니다. AI 서비스가 현재 연결되지 않았습니다."

    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        system_instruction = """
        당신은 'Settlo Mate'입니다. 외국인 유학생들이 한국에서 잘 정착하도록 돕는 친절한 AI 친구입니다.
        비자 문제, 한국 문화, 쓰레기 분리수거, 맛집 추천 등 생활 전반에 대해 친절하고 명확하게 한국어로 답변해주세요.
        답변은 3~5문장 내외로 간결하게 핵심만 전달하세요. 이모지(😊)를 적절히 사용해 주세요.
        """
        
        response = model.generate_content(f"{system_instruction}\n\n사용자 질문: {user_message}")
        return response.text
        
    except Exception as e:
        return f"답변 생성 중 오류가 발생했습니다: {str(e)}"
    
# ---------------------------------------------------------
# [신규] 감사 로그 (Audit Log) 기록
# ---------------------------------------------------------
def log_action(db: Session, user_id: int, action: str, target_id: int = 0):
    """
    주요 활동(업로드, 조회, 상태변경)을 DB에 기록합니다.
    """
    new_log = models.AuditLog(
        user_id=user_id,
        action=action,
        target_id=target_id
    )
    db.add(new_log)
    db.commit()