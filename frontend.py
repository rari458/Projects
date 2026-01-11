import streamlit as st
import requests
from datetime import datetime, date
import pandas as pd
import time
import json

# 페이지 설정
st.set_page_config(page_title="Settlo", layout="wide", page_icon="🌏")

# API 주소
API_URL = "https://settlo-647487045104.asia-northeast3.run.app"

# --------------------------------------------------------------------------
# [Data] 국가 목록 (주요 유학생 출신 국가 포함)
# --------------------------------------------------------------------------
COUNTRY_LIST = [
    "Antigua and Barbuda (ATG)",
    "Arab Republic of Egypt (EGY)",
    "Argentine Republic (ARG)",
    "Barbados (BRB)",
    "Belize (BLZ)",
    "Bolivarian Republic of Venezuela (VEN)",
    "Bosnia and Herzegovina (BIH)",
    "Brunei Darussalam (BRN)",
    "Burkina Faso (BFA)",
    "Canada (CAN)",
    "Central African Republic (CAF)",
    "Commonwealth of Australia (AUS)",
    "Commonwealth of Dominica (DMA)",
    "Commonwealth of the Bahamas (BHS)",
    "Co-operative Republic of Guyana (GUY)",
    "Czech Republic (CZE)",
    "Democratic People's Republic of Korea (PRK)",
    "Democratic Republic of Sao Tome and Principe (STP)",
    "Democratic Republic of the Congo (COD)",
    "Democratic Republic of Timor-Leste (TLS)",
    "Democratic Socialist Republic of Sri Lanka (LKA)",
    "Dominican Republic (DOM)",
    "Federal Democratic Republic of Ethiopia (ETH)",
    "Federal Democratic Republic of Nepal (NPL)",
    "Federal Republic of Germany (DEU)",
    "Federal Republic of Nigeria (NGA)",
    "Federal Republic of Somalia (SOM)",
    "Federated States of Micronesia (FSM)",
    "Federative Republic of Brazil (BRA)",
    "French Republic (FRA)",
    "Gabonese Republic (GAB)",
    "Georgia (GEO)",
    "Grand Duchy of Luxembourg (LUX)",
    "Grenada (GRD)",
    "Hashemite Kingdom of Jordan (JOR)",
    "Hellenic Republic (GRC)",
    "Holy See (VAT)",
    "Hungary (HUN)",
    "Iceland (ISL)",
    "Independent State of Papua New Guinea (PNG)",
    "Independent State of Samoa (WSM)",
    "Ireland (IRL)",
    "Islamic Republic of Afghanistan (AFG)",
    "Islamic Republic of Iran (IRN)",
    "Islamic Republic of Mauritania (MRT)",
    "Islamic Republic of Pakistan (PAK)",
    "Italian Republic (ITA)",
    "Jamaica (JAM)",
    "Japan (JPN)",
    "Kingdom of Bahrain (BHR)",
    "Kingdom of Belgium (BEL)",
    "Kingdom of Bhutan (BTN)",
    "Kingdom of Cambodia (KHM)",
    "Kingdom of Denmark (DNK)",
    "Kingdom of Eswatini (SWZ)",
    "Kingdom of Lesotho (LSO)",
    "Kingdom of Morocco (MAR)",
    "Kingdom of Norway (NOR)",
    "Kingdom of Saudi Arabia (SAU)",
    "Kingdom of Spain (ESP)",
    "Kingdom of Sweden (SWE)",
    "Kingdom of Thailand (THA)",
    "Kingdom of the Netherlands (NLD)",
    "Kingdom of Tonga (TON)",
    "Kyrgyz Republic (KGZ)",
    "Lao People's Democratic Republic (LAO)",
    "Lebanese Republic (LBN)",
    "Malaysia (MYS)",
    "Mongolia (MNG)",
    "Montenegro (MNE)",
    "New Zealand (NZL)",
    "Oriental Republic of Uruguay (URY)",
    "People's Democratic Republic of Algeria (DZA)",
    "People's Republic of Bangladesh (BGD)",
    "People's Republic of China (CHN)",
    "Plurinational State of Bolivia (BOL)",
    "Portuguese Republic (PRT)",
    "Principality of Andorra (AND)",
    "Principality of Liechtenstein (LIE)",
    "Principality of Monaco (MCO)",
    "Republic of Albania (ALB)",
    "Republic of Angola (AGO)",
    "Republic of Armenia (ARM)",
    "Republic of Austria (AUT)",
    "Republic of Azerbaijan (AZE)",
    "Republic of Belarus (BLR)",
    "Republic of Benin (BEN)",
    "Republic of Botswana (BWA)",
    "Republic of Bulgaria (BGR)",
    "Republic of Burundi (BDI)",
    "Republic of Cabo Verde (CPV)",
    "Republic of Cameroon (CMR)",
    "Republic of Chad (TCD)",
    "Republic of Chile (CHL)",
    "Republic of Colombia (COL)",
    "Republic of Costa Rica (CRI)",
    "Republic of Cote d'Ivoire (CIV)",
    "Republic of Croatia (HRV)",
    "Republic of Cuba (CUB)",
    "Republic of Cyprus (CYP)",
    "Republic of Djibouti (DJI)",
    "Republic of Ecuador (ECU)",
    "Republic of El Salvador (SLV)",
    "Republic of Equatorial Guinea (GNQ)",
    "Republic of Estonia (EST)",
    "Republic of Fiji (FJI)",
    "Republic of Finland (FIN)",
    "Republic of Ghana (GHA)",
    "Republic of Guatemala (GTM)",
    "Republic of Guinea (GIN)",
    "Republic of Guinea-Bissau (GNB)",
    "Republic of Haiti (HTI)",
    "Republic of Honduras (HND)",
    "Republic of India (IND)",
    "Republic of Indonesia (IDN)",
    "Republic of Iraq (IRQ)",
    "Republic of Kazakhstan (KAZ)",
    "Republic of Kenya (KEN)",
    "Republic of Kiribati (KIR)",
    "Republic of Korea (KOR)",
    "Republic of Latvia (LVA)",
    "Republic of Liberia (LBR)",
    "Republic of Lithuania (LTU)",
    "Republic of Madagascar (MDG)",
    "Republic of Malawi (MWI)",
    "Republic of Maldives (MDV)",
    "Republic of Mali (MLI)",
    "Republic of Malta (MLT)",
    "Republic of Mauritius (MUS)",
    "Republic of Moldova (MDA)",
    "Republic of Mozambique (MOZ)",
    "Republic of Namibia (NAM)",
    "Republic of Nauru (NRU)",
    "Republic of Nicaragua (NIC)",
    "Republic of North Macedonia (MKD)",
    "Republic of Palau (PLW)",
    "Republic of Panama (PAN)",
    "Republic of Paraguay (PRY)",
    "Republic of Peru (PER)",
    "Republic of Poland (POL)",
    "Republic of Rwanda (RWA)",
    "Republic of San Marino (SMR)",
    "Republic of Senegal (SEN)",
    "Republic of Serbia (SRB)",
    "Republic of Seychelles (SYC)",
    "Republic of Sierra Leone (SLE)",
    "Republic of Singapore (SGP)",
    "Republic of Slovenia (SVN)",
    "Republic of South Africa (ZAF)",
    "Republic of South Sudan (SSD)",
    "Republic of Suriname (SUR)",
    "Republic of Tajikistan (TJK)",
    "Republic of the Congo (COG)",
    "Republic of the Gambia (GMB)",
    "Republic of the Marshall Islands (MHL)",
    "Republic of the Niger (NER)",
    "Republic of the Philippines (PHL)",
    "Republic of the Sudan (SDN)",
    "Republic of the Union of Myanmar (MMR)",
    "Republic of Trinidad and Tobago (TTO)",
    "Republic of Tunisia (TUN)",
    "Republic of Türkiye (TUR)",
    "Republic of Uganda (UGA)",
    "Republic of Uzbekistan (UZB)",
    "Republic of Vanuatu (VUT)",
    "Republic of Yemen (YEM)",
    "Republic of Zambia (ZMB)",
    "Republic of Zimbabwe (ZWE)",
    "Romania (ROU)",
    "Russian Federation (RUS)",
    "Saint Kitts and Nevis (KNA)",
    "Saint Lucia (LCA)",
    "Saint Vincent and the Grenadines (VCT)",
    "Slovak Republic (SVK)",
    "Socialist Republic of Viet Nam (VNM)",
    "Solomon Islands (SLB)",
    "State of Eritrea (ERI)",
    "State of Israel (ISR)",
    "State of Kuwait (KWT)",
    "State of Libya (LBY)",
    "State of Palestine (PSE)",
    "State of Qatar (QAT)",
    "Sultanate of Oman (OMN)",
    "Swiss Confederation (CHE)",
    "Syrian Arab Republic (SYR)",
    "Togolese Republic (TGO)",
    "Turkmenistan (TKM)",
    "Tuvalu (TUV)",
    "Ukraine (UKR)",
    "Union of the Comoros (COM)",
    "United Arab Emirates (ARE)",
    "United Kingdom of Great Britain and Northern Ireland (GBR)",
    "United Mexican States (MEX)",
    "United Republic of Tanzania (TZA)",
    "United States of America (USA)",
    "Other"
]

# --------------------------------------------------------------------------
# [i18n] 다국어 번역 딕셔너리 (한국어 / English)
# --------------------------------------------------------------------------
TL = {
    "KO": {
        "title": "🌏 Settlo",
        "subtitle": "외국인 유학생을 위한 AI 정착 플랫폼",
        "tabs_login": ["🔑 로그인", "✨ 회원가입"],
        "label_id": "아이디 (ID)",
        "label_pw": "비밀번호 (Password)",
        "btn_login": "로그인 하기",
        "label_email": "이메일 주소",
        "label_name": "이름 (Full Name)",
        "btn_signup": "가입하기",
        "msg_login_success": "로그인 성공!",
        "msg_login_fail": "아이디 또는 비밀번호가 잘못되었습니다.",
        "msg_signup_success": "가입되었습니다! 로그인 탭에서 로그인해주세요.",
        "welcome": "반가워요, {name}님! 👋",
        "menu_info": "🏫 내 정착 정보",
        "label_univ": "소속 대학교",
        "label_region": "거주 지역",
        "menu_alert": "🔔 알림 센터",
        "alert_none": "예정된 급한 일정이 없습니다. ☕",
        "menu_visa": "⚙️ 내 체류 정보",
        "label_visa": "비자 타입",
        "warn_visa_change": "비자 변경 시 로드맵이 초기화됩니다.",
        "btn_save": "변경사항 저장",
        "btn_logout": "로그아웃",
        "tabs_main": ["🏠 홈", "🛤️ 워크플로우", "📂 문서 지갑", "💬 AI 상담", "🗣️ 커뮤니티", "📍 기관 찾기"],
        "home_greeting": "안녕하세요, {name}님!",
        "home_desc": "한국 정착을 위한 필수 과정을 안내해 드립니다.",
        "home_sec1": "##### 🏛️ 기관별 업무 탐색",
        "btn_school": "🏫\n학교",
        "btn_admin": "🏢\n행정",
        "btn_bank": "🏦\n은행",
        "btn_sim": "📡\n통신",
        "btn_house": "🏠\n주거",
        "home_sec2": "##### 🔥 우선 해결해야 할 항목",
        "btn_view": "보기",
        "msg_no_priority": "현재 대기 중인 우선 항목이 없습니다! 워크플로우 탭을 확인해보세요.",
        "back_home": "← {cat} 탐색 종료 (홈으로)",
        "cat_title": "📂 {cat} 관련 업무",
        "msg_no_cat_items": "아직 '{cat}' 카테고리에 등록된 항목이 없습니다.",
        "cat_school": "학교/수강신청", "cat_visa": "행정/비자", "cat_bank": "은행/금융", "cat_sim": "통신/유심", "cat_housing": "주거/부동산",
        "back_prev": "← 뒤로가기",
        "preview_insight": "💡 유학생의 82%가 입국 후 1주 이내에 완료하는 절차입니다.",
        "metric_time": "평균 소요 시간",
        "metric_visit": "방문 필요 여부",
        "preview_sec1": "### ■ 이런 경우에 필요해요",
        "preview_txt1": "- 한국에서의 공식 신분 증명이 필요할 때",
        "preview_txt2": "- 은행 계좌 개설 및 휴대폰 개통 시",
        "btn_start": "🚀 바로 시작하기 (워크플로우에 추가)",
        "toast_start": "{title} 항목이 시작되었습니다!",
        "wf_title": "나의 워크플로우",
        "wf_ing": "🔵 진행중",
        "wf_hold": "🟡 보류",
        "wf_done": "🟢 완료",
        "btn_detail": "상세",
        "step_s1": "#### STEP 1. 방문 및 준비",
        "step_s2": "#### STEP 2. 문서 제출 및 검토",
        "step_checklist": "**☑ 방문 전 준비물 (Checklist)**",
        "no_checklist": "체크리스트 없음",
        "file_submit_success": "제출되었습니다!",
        "map_nearby": "#### 📍 내 주변 방문 기관",
        "help_title": "#### 💬 도움말",
        "btn_faq": "FAQ\n보기",
        "btn_ask": "전문가\n질문",
        "btn_finish": "🎉 이 단계 완료하기 (Next Step)",
        "btn_finish_disable": "완료 (체크리스트 확인 필요)",
        "wallet_title": "📂 내 문서 보관함",
        "wallet_add": "➕ 새 문서 등록 및 분석하기",
        "wallet_info": "여권이나 계약서를 업로드하면 AI가 진위 여부와 독소 조항을 분석합니다.",
        "label_doc_type": "문서 종류",
        "opt_doc": ["🛂 여권/등록증", "📜 임대차/근로 계약서"],
        "label_file": "파일 선택",
        "btn_upload_analyze": "업로드 및 분석 시작",
        "msg_upload_success": "등록 및 분석 완료! 아래 목록에서 확인하세요.",
        "wallet_list": "### 📜 저장된 문서",
        "msg_no_docs": "아직 저장된 문서가 없습니다. 위에서 문서를 추가해보세요!",
        "stat_verified": "✅ 승인됨",
        "stat_review": "🟡 검토중",
        "stat_rejected": "🚫 반려됨",
        "stat_unverified": "⏳ 미인증",
        "exp_details": "상세 보기",
        "chat_title": "💬 AI 컨시어지",
        "chat_placeholder": "질문하세요 (예: 비자 연장은 어떻게 해?)",
        "com_title": "🗣️ 커뮤니티",
        "com_write": "📝 새 글 작성하기",
        "label_board": "게시판 선택",
        "opt_board": ["후기 게시판", "정보 공유", "Q&A (질문)"],
        "label_title": "제목",
        "label_content": "내용",
        "btn_register": "등록",
        "msg_reg_success": "등록되었습니다!",
        "msg_no_posts": "게시글이 없습니다.",
        "tabs_com": ["📢 승인/반려 후기", "💡 정보 게시판", "❓ Q&A"],
        "toggle_verified": "✅ 검증된 글만 보기",
        "map_title": "📍 기관 찾기",
        "label_standard": "**기준: {univ}**",
        "map_rec": "#### 🎯 {univ} 주변 추천",
        "opt_agency": ["🏦 은행", "🏢 관공서", "✈️ 출입국"],
        "btn_nav": "길찾기",
        "admin_mode": "🔒 관리자 모드",
        "admin_title": "🔒 관리자(Admin) 대시보드",
        "admin_tabs": ["📄 문서 검토 대기", "📅 예약 현황", "📢 정보글 검증"],
        "btn_approve": "✅ 승인",
        "btn_reject": "🚫 반려",
        "btn_verify": "🏅 검증 마크 부여",
        "setup_title": "👋 환영합니다!",
        "setup_desc": "맞춤형 서비스를 위해 초기 정보를 설정해주세요.",
        "label_nat": "국적 (Nationality)",
        "label_entry": "입국일 (Entry Date)",
        "btn_start_app": "설정 저장 및 시작하기",
        "btn_edit": "✏️ 수정",
        "btn_delete": "🗑️ 삭제",
        "btn_update": "수정 완료",
        "msg_delete_confirm": "삭제되었습니다.",
        "msg_update_success": "수정되었습니다.",
        "label_comment": "댓글 작성",
        "btn_add_comment": "💬 댓글 등록",
        "header_comments": "댓글 ({count})",
        "msg_no_comments": "첫 번째 댓글을 남겨보세요!",
        "label_edit_title": "제목 수정",
        "label_edit_content": "내용 수정"
    },
    "EN": {
        "title": "🌏 Settlo",
        "subtitle": "AI Settlement Platform for International Students",
        "tabs_login": ["🔑 Login", "✨ Sign Up"],
        "label_id": "Username (ID)",
        "label_pw": "Password",
        "btn_login": "Log In",
        "label_email": "Email Address",
        "label_name": "Full Name",
        "btn_signup": "Sign Up",
        "msg_login_success": "Login Successful!",
        "msg_login_fail": "Incorrect username or password.",
        "msg_signup_success": "Signed up! Please log in.",
        "welcome": "Welcome, {name}! 👋",
        "menu_info": "🏫 My Settlement Info",
        "label_univ": "University",
        "label_region": "Region",
        "menu_alert": "🔔 Notification Center",
        "alert_none": "No urgent schedules. ☕",
        "menu_visa": "⚙️ Visa Status",
        "label_visa": "Visa Type",
        "warn_visa_change": "Changing visa type will reset your roadmap.",
        "btn_save": "Save Changes",
        "btn_logout": "Log Out",
        "tabs_main": ["🏠 Home", "🛤️ Workflow", "📂 Doc Wallet", "💬 AI Chat", "🗣️ Community", "📍 Map"],
        "home_greeting": "Hello, {name}!",
        "home_desc": "Here is your essential guide to settling in Korea.",
        "home_sec1": "##### 🏛️ Explore by Category",
        "btn_school": "🏫\nSchool",
        "btn_admin": "🏢\nAdmin",
        "btn_bank": "🏦\nBank",
        "btn_sim": "📡\nSIM/Mobile",
        "btn_house": "🏠\nHousing",
        "home_sec2": "##### 🔥 Priority Items",
        "btn_view": "View",
        "msg_no_priority": "No priority items waiting! Check your workflow tab.",
        "back_home": "← Close {cat} (Back to Home)",
        "cat_title": "📂 {cat} Tasks",
        "msg_no_cat_items": "No items found in '{cat}' category yet.",
        "cat_school": "School", "cat_visa": "Visa/Admin", "cat_bank": "Banking", "cat_sim": "Mobile/SIM", "cat_housing": "Housing",
        "back_prev": "← Go Back",
        "preview_insight": "💡 82% of students complete this within 1 week of arrival.",
        "metric_time": "Avg. Time",
        "metric_visit": "Visit Required",
        "preview_sec1": "### ■ When do you need this?",
        "preview_txt1": "- When official identification is required in Korea",
        "preview_txt2": "- Opening a bank account or getting a mobile plan",
        "btn_start": "🚀 Start Now (Add to Workflow)",
        "toast_start": "{title} has started!",
        "wf_title": "My Workflow",
        "wf_ing": "🔵 In Progress",
        "wf_hold": "🟡 On Hold",
        "wf_done": "🟢 Completed",
        "btn_detail": "Detail",
        "step_s1": "#### STEP 1. Visit & Prep",
        "step_s2": "#### STEP 2. Submit Documents",
        "step_checklist": "**☑ Preparation Checklist**",
        "no_checklist": "No Checklist",
        "file_submit_success": "Submitted successfully!",
        "map_nearby": "#### 📍 Nearby Agencies",
        "help_title": "#### 💬 Help",
        "btn_faq": "View\nFAQ",
        "btn_ask": "Ask\nExpert",
        "btn_finish": "🎉 Complete Step (Next)",
        "btn_finish_disable": "Complete (Checklist Needed)",
        "wallet_title": "📂 My Document Wallet",
        "wallet_add": "➕ Register & Analyze New Doc",
        "wallet_info": "Upload passports or contracts for AI risk analysis.",
        "label_doc_type": "Document Type",
        "opt_doc": ["🛂 Passport/ID", "📜 Contract"],
        "label_file": "Choose File",
        "btn_upload_analyze": "Upload & Analyze",
        "msg_upload_success": "Upload & Analysis Complete! Check below.",
        "wallet_list": "### 📜 Saved Documents",
        "msg_no_docs": "No saved documents yet. Add one above!",
        "stat_verified": "✅ Verified",
        "stat_review": "🟡 In Review",
        "stat_rejected": "🚫 Rejected",
        "stat_unverified": "⏳ Unverified",
        "exp_details": "View Details",
        "chat_title": "💬 AI Concierge",
        "chat_placeholder": "Ask anything (e.g., How to extend D-2 visa?)",
        "com_title": "🗣️ Community",
        "com_write": "📝 Write New Post",
        "label_board": "Board Type",
        "opt_board": ["Reviews", "Information", "Q&A"],
        "label_title": "Title",
        "label_content": "Content",
        "btn_register": "Post",
        "msg_reg_success": "Registered successfully!",
        "msg_no_posts": "No posts here.",
        "tabs_com": ["📢 Reviews", "💡 Info Board", "❓ Q&A"],
        "toggle_verified": "✅ Verified Posts Only",
        "map_title": "📍 Find Agencies",
        "label_standard": "**Based on: {univ}**",
        "map_rec": "#### 🎯 Recommended near {univ}",
        "opt_agency": ["🏦 Bank", "🏢 Office", "✈️ Immigration"],
        "btn_nav": "Navigate",
        "admin_mode": "🔒 Admin Mode",
        "admin_title": "🔒 Admin Dashboard",
        "admin_tabs": ["📄 Pending Docs", "📅 Reservations", "📢 Verify Info"],
        "btn_approve": "✅ Approve",
        "btn_reject": "🚫 Reject",
        "btn_verify": "🏅 Verify Post",
        "setup_title": "👋 Welcome!",
        "setup_desc": "Please set up your profile for personalized service.",
        "label_nat": "Nationality",
        "label_entry": "Entry Date",
        "btn_start_app": "Save & Start",
        "btn_edit": "✏️ Edit",
        "btn_delete": "🗑️ Delete",
        "btn_update": "Update",
        "msg_delete_confirm": "Deleted successfully.",
        "msg_update_success": "Updated successfully.",
        "label_comment": "Write a comment",
        "btn_add_comment": "💬 Add Comment",
        "header_comments": "Comments ({count})",
        "msg_no_comments": "Be the first to comment!",
        "label_edit_title": "Edit Title",
        "label_edit_content": "Edit Content"
    }
}

# 세션 상태 초기화
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "visa_type" not in st.session_state:
    st.session_state.visa_type = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "page_view" not in st.session_state:
    st.session_state.page_view = "HOME"
if "selected_step" not in st.session_state:
    st.session_state.selected_step = None
if "selected_category" not in st.session_state:
    st.session_state.selected_category = None
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "language" not in st.session_state:
    st.session_state.language = "KO"

# 다국어 텍스트 가져오기 함수
def get_txt(key):
    lang = st.session_state.language
    return TL[lang].get(key, key)

# ==========================================
# 1. 로그인 / 회원가입 화면
# ==========================================
def login_page():
    st.title(get_txt("title"))
    st.subheader(get_txt("subtitle"))
    
    # [i18n] 언어 선택 (로그인 전에도 가능하게)
    lang_opt = st.radio("Language / 언어", ["한국어", "English"], horizontal=True, key="login_lang")
    st.session_state.language = "KO" if lang_opt == "한국어" else "EN"

    tab1, tab2 = st.tabs(get_txt("tabs_login"))

    with tab1:
        with st.container(border=True):
            login_id = st.text_input(get_txt("label_id"), key="login_id")
            login_pw = st.text_input(get_txt("label_pw"), type="password", key="login_pw")
            
            if st.button(get_txt("btn_login"), width="stretch"):
                data = {"username": login_id, "password": login_pw}
                try:
                    res = requests.post(f"{API_URL}/token", data=data)
                    if res.status_code == 200:
                        token_data = res.json()
                        st.session_state.access_token = token_data["access_token"]
                        st.session_state.user_id = token_data.get("user_id")
                        st.session_state.user_name = token_data.get("user_name")
                        st.session_state.visa_type = token_data.get("visa_type")
                        st.session_state.is_admin = token_data.get("is_admin", False)
                        st.success(get_txt("msg_login_success"))
                        st.rerun()
                    else:
                        st.error(get_txt("msg_login_fail"))
                except Exception as e:
                    st.error(f"Connection Error: {e}")

    with tab2:
        with st.container(border=True):
            new_id = st.text_input(get_txt("label_id"), key="new_id")
            new_pw = st.text_input(get_txt("label_pw"), type="password", key="new_pw")
            new_email = st.text_input(get_txt("label_email"), key="new_email")
            new_name = st.text_input(get_txt("label_name"), key="new_name")
            
            if st.button(get_txt("btn_signup"), width="stretch"):
                if new_id and new_pw and new_email and new_name:
                    payload = {"username": new_id, "password": new_pw, "email": new_email, "full_name": new_name}
                    try:
                        res = requests.post(f"{API_URL}/users/signup", json=payload)
                        if res.status_code == 200:
                            st.success(get_txt("msg_signup_success"))
                        else:
                            st.error(f"Error: {res.text}")
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.warning("Please fill all fields.")

# ==========================================
# 2. 초기 정보 설정 (수정됨)
# ==========================================
def setup_profile_page():
    # [i18n] 간단하게 언어 토글 추가
    lang_opt = st.radio("Language / 언어", ["한국어", "English"], horizontal=True, key="setup_lang")
    st.session_state.language = "KO" if lang_opt == "한국어" else "EN"

    st.title(get_txt("setup_title"))
    st.info(get_txt("setup_desc"))
    
    with st.form("setup_form"):
        col1, col2 = st.columns(2)
        with col1:
            # [수정] text_input -> selectbox로 변경 (COUNTRY_LIST 활용)
            nationality = st.selectbox(get_txt("label_nat"), COUNTRY_LIST, index=COUNTRY_LIST.index("Republic of Korea (KOR)") if "Republic of Korea (KOR)" in COUNTRY_LIST else 0)
            entry_date = st.date_input(get_txt("label_entry"), date.today())
        with col2:
            visa = st.selectbox(get_txt("label_visa"), ["D-2", "D-4"])
        
        # use_container_width=True 제거
        if st.form_submit_button(get_txt("btn_start_app")):
            if st.session_state.user_id:
                payload = {"nationality": nationality, "visa_type": visa, "entry_date": str(entry_date)}
                try:
                    res = requests.patch(f"{API_URL}/users/{st.session_state.user_id}/visa", json=payload)
                    if res.status_code == 200:
                        st.session_state.visa_type = visa
                        st.rerun()
                    else: st.error("Save Failed")
                except Exception as e: st.error(f"Error: {e}")

# ==========================================
# 3. 메인 대시보드
# ==========================================
def main_dashboard():
    # [i18n] 사이드바 언어 선택
    with st.sidebar:
        lang_opt = st.radio("Language / 언어", ["한국어", "English"], horizontal=True, key="main_lang")
        st.session_state.language = "KO" if lang_opt == "한국어" else "EN"
        
        st.header(get_txt("welcome").format(name=st.session_state.user_name))
        
        # 관리자일 경우 로그아웃만 표시
        if st.session_state.get("is_admin", False):
            st.divider()
            if st.button(get_txt("btn_logout"), width="stretch"):
                for key in list(st.session_state.keys()): del st.session_state[key]
                st.rerun()
            # 관리자 전용 화면 로직은 아래에서 처리
    
    # 관리자 모드 처리
    if st.session_state.get("is_admin", False):
        st.title(get_txt("admin_title"))
        ad_tab1, ad_tab2, ad_tab3 = st.tabs(get_txt("admin_tabs"))
        
        with ad_tab1:
            try:
                pending_docs = requests.get(f"{API_URL}/admin/pending-documents").json()
                if not pending_docs: st.success("No pending documents.")
                else:
                    for doc in pending_docs:
                        with st.container(border=True):
                            c1, c2, c3 = st.columns([2, 2, 1])
                            c1.markdown(f"**Doc ID: {doc['id']}** ({doc['doc_type']})")
                            c1.caption(f"User: {doc['user_id']} | Date: {doc['uploaded_at'][:10]}")
                            import json
                            try:
                                summary = json.loads(doc['risk_analysis']).get('summary', '-')
                                c2.info(f"AI: {summary}")
                            except: c2.caption("No AI Data")
                            with c3:
                                if st.button(get_txt("btn_approve"), key=f"ok_{doc['id']}", width="stretch"):
                                    requests.patch(f"{API_URL}/documents/{doc['id']}/status", json={"status": "VERIFIED"})
                                    st.rerun()
                                if st.button(get_txt("btn_reject"), key=f"no_{doc['id']}", width="stretch"):
                                    requests.patch(f"{API_URL}/documents/{doc['id']}/status", json={"status": "REJECTED"})
                                    st.rerun()
            except Exception as e:
                st.error(f"Load Failed: {e}")
        
        with ad_tab2:
            try:
                res_list = requests.get(f"{API_URL}/admin/reservations").json()
                if res_list:
                    df = pd.DataFrame(res_list)[['partner_name', 'reservation_date', 'reservation_time', 'user_id', 'memo']]
                    st.dataframe(df, width="stretch")
                else: st.info("No reservations.")
            except: st.error("Load Failed")
            
        with ad_tab3:
            try:
                posts = requests.get(f"{API_URL}/community/posts?category=INFO").json()
                unverified = [p for p in posts if not p['is_verified']]
                if not unverified: st.success("No unverified posts.")
                else:
                    for p in unverified:
                        with st.expander(f"{p['title']} (User: {p['author_id']})"):
                            st.write(p['content'])
                            if st.button(get_txt("btn_verify"), key=f"v_post_{p['id']}"):
                                requests.patch(f"{API_URL}/community/posts/{p['id']}/verify", json={"is_verified": True})
                                st.rerun()
            except: st.error("Load Failed")
        return # 관리자 모드 종료

    # --- 일반 사용자 모드 ---
    
    # 예약 모달
    @st.dialog("📅 Reservation")
    def open_reservation_dialog(partner_name):
        st.write(f"Booking with **'{partner_name}'**")
        with st.form("res_form"):
            d = st.date_input("Date", date.today())
            t = st.time_input("Time", datetime.now().time())
            memo = st.text_area("Request", placeholder="Enter your request...")
            if st.form_submit_button("Confirm"):
                payload = {"partner_name": partner_name, "reservation_date": str(d), "reservation_time": str(t), "memo": memo}
                try:
                    res = requests.post(f"{API_URL}/reservations?user_id={st.session_state.user_id}", json=payload)
                    if res.status_code == 200:
                        st.success("Confirmed!")
                        time.sleep(1)
                        st.rerun()
                    else: st.error("Failed")
                except Exception as e: st.error(f"Error: {e}")

    # 사이드바 (사용자용)
    with st.sidebar:
        st.markdown(f"### {get_txt('menu_info')}")
        univ_list = ["연세대학교 (Sinchon)", "서울대학교 (Gwanak)", "고려대학교 (Anam)", "한양대학교 (Seoul)"]
        my_univ = st.selectbox(get_txt("label_univ"), univ_list, index=0)
        
        region_list = ["서대문구 (Seodaemun)", "관악구 (Gwanak)", "성북구 (Seongbuk)", "마포구 (Mapo)"]
        my_region = st.selectbox(get_txt("label_region"), region_list, index=0)

        st.divider()
        st.markdown(f"### {get_txt('menu_alert')}")
        with st.container(border=True):
            if st.session_state.user_id:
                try:
                    res = requests.get(f"{API_URL}/users/{st.session_state.user_id}/roadmap")
                    if res.status_code == 200:
                        steps = res.json().get('steps', [])
                        alerts = []
                        today = date.today()
                        for s in steps:
                            if s['status'] != "완료" and s['deadline']:
                                d_date = datetime.strptime(s['deadline'], "%Y-%m-%d").date()
                                days_left = (d_date - today).days
                                if 0 <= days_left <= 7:
                                    alerts.append(f"🚨 **{s['title']}** D-{days_left}!")
                                elif days_left < 0:
                                    alerts.append(f"🔥 **{s['title']}** Overdue!")
                        if alerts:
                            for a in alerts: st.markdown(a)
                        else:
                            st.caption(get_txt("alert_none"))
                except: st.caption("Loading...")
        
        st.divider()
        st.markdown(f"### {get_txt('menu_visa')}")
        visa_options = ["D-2", "D-4"]
        current_visa = st.session_state.get('visa_type', 'D-2')
        try: default_ix = visa_options.index(current_visa)
        except: default_ix = 0
        selected_visa = st.selectbox(get_txt("label_visa"), visa_options, index=default_ix)
        if selected_visa != current_visa:
            st.warning(get_txt("warn_visa_change"))
            if st.button(get_txt("btn_save"), width="stretch"):
                try:
                    payload = {"visa_type": selected_visa}
                    requests.patch(f"{API_URL}/users/{st.session_state.user_id}/visa", json=payload)
                    st.session_state.visa_type = selected_visa
                    st.success("Updated!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")

        st.divider()
        if st.button(get_txt("btn_logout"), width="stretch"):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    # --- 메인 탭 ---
    tab_home, tab_workflow, tab_wallet, tab_chat, tab_community, tab_map = st.tabs(get_txt("tabs_main"))

    # 로드맵 데이터 가져오기
    steps = []
    if st.session_state.user_id:
        try:
            res = requests.get(f"{API_URL}/users/{st.session_state.user_id}/roadmap")
            if res.status_code == 200:
                steps = res.json().get('steps', [])
        except: pass

    # =========================================================================
    # [탭 1] 홈 화면 (탐색 & 미리보기 & 기관별 리스트)
    # =========================================================================
    with tab_home:
        # 화면 상태 관리를 위한 변수 초기화
        if "selected_category" not in st.session_state:
            st.session_state.selected_category = None

        # ---------------------------------------------------------
        # [화면 A] 카테고리별 전체 리스트 보기
        # ---------------------------------------------------------
        if st.session_state.page_view == "CATEGORY_LIST":
            cat = st.session_state.selected_category
            # 카테고리 이름 i18n 처리
            cat_key = f"cat_{cat.lower()}" if cat else "cat_visa"
            cat_name = get_txt(cat_key) 
            
            if st.button(get_txt("back_home").format(cat=cat_name), key="back_from_cat"):
                st.session_state.page_view = "HOME"
                st.rerun()
            
            st.subheader(get_txt("cat_title").format(cat=cat_name))
            filtered = [s for s in steps if s.get('category') == cat]
            
            if filtered:
                for step in filtered:
                    with st.container(border=True):
                        c1, c2 = st.columns([4, 1])
                        with c1:
                            st.markdown(f"**{step['title']}**")
                            st.caption(f"Status: {step['status']}")
                        with c2:
                            if st.button(get_txt("btn_view"), key=f"cat_{step['id']}"):
                                st.session_state.selected_step = step
                                st.session_state.page_view = "PREVIEW"
                                st.rerun()
            else:
                st.info(get_txt("msg_no_cat_items").format(cat=cat_name))

        # ---------------------------------------------------------
        # [화면 B] 항목 상세 미리보기 (Preview)
        # ---------------------------------------------------------
        elif st.session_state.page_view == "PREVIEW":
            step = st.session_state.selected_step
            if step:
                if st.button(get_txt("back_prev")):
                    st.session_state.page_view = "HOME"
                    st.rerun()
                
                st.title(step['title'])
                st.markdown(f"**{step['description']}**")
                
                st.info(get_txt("preview_insight"))
                
                c1, c2 = st.columns(2)
                c1.metric(get_txt("metric_time"), "1~3 Days") 
                c2.metric(get_txt("metric_visit"), "1 Visit")
                
                st.markdown(get_txt("preview_sec1"))
                st.write(get_txt("preview_txt1"))
                st.write(get_txt("preview_txt2"))
                
                st.divider()
                
                # [수정됨] 워크플로우 추가 버튼 (에러 핸들링 강화)
                if st.button(get_txt("btn_start"), type="primary", width="stretch"):
                    try:
                        res = requests.patch(f"{API_URL}/roadmap-steps/{step['id']}", json={"status": "진행중"})
                        
                        if res.status_code == 200:
                            st.toast(get_txt("toast_start").format(title=step['title']))
                            time.sleep(1)
                            st.session_state.page_view = "HOME" 
                            st.rerun()
                        else:
                            st.error(f"Failed to start: {res.status_code} - {res.text}")
                            
                    except Exception as e: 
                        st.error(f"Connection Error: {e}")

        # ---------------------------------------------------------
        # [화면 C] 기본 메인 홈 화면 (그 외 모든 경우)
        # ---------------------------------------------------------
        else:
            # 다른 탭에서 왔을 때 page_view가 WORKFLOW 등으로 되어있을 수 있으므로 강제 보정은 하지 않더라도
            # else로 받아주면 화면이 렌더링 됩니다.
            
            st.subheader(get_txt("home_greeting").format(name=st.session_state.user_name))
            st.markdown(get_txt("home_desc"))
            
            # 1. 상단 아이콘
            st.markdown(get_txt("home_sec1"))
            c1, c2, c3, c4, c5 = st.columns(5)
            
            if c1.button(get_txt("btn_school"), width="stretch"):
                st.session_state.selected_category = "SCHOOL"
                st.session_state.page_view = "CATEGORY_LIST"
                st.rerun()
            
            if c2.button(get_txt("btn_admin"), width="stretch"):
                st.session_state.selected_category = "VISA"
                st.session_state.page_view = "CATEGORY_LIST"
                st.rerun()

            if c3.button(get_txt("btn_bank"), width="stretch"):
                st.session_state.selected_category = "BANK"
                st.session_state.page_view = "CATEGORY_LIST"
                st.rerun()

            if c4.button(get_txt("btn_sim"), width="stretch"):
                st.session_state.selected_category = "SIM"
                st.session_state.page_view = "CATEGORY_LIST"
                st.rerun()

            if c5.button(get_txt("btn_house"), width="stretch"):
                st.session_state.selected_category = "HOUSING"
                st.session_state.page_view = "CATEGORY_LIST"
                st.rerun()

            st.divider()

            # 2. 우선 항목 리스트
            st.markdown(get_txt("home_sec2"))
            waiting_steps = [s for s in steps if s['status'] == '대기']
            
            if waiting_steps:
                for step in waiting_steps:
                    with st.container(border=True):
                        col_txt, col_btn = st.columns([4, 1])
                        with col_txt:
                            st.markdown(f"**{step['title']}**")
                            st.caption(f"{step['description'][:40]}...")
                        with col_btn:
                            if st.button(get_txt("btn_view"), key=f"pre_{step['id']}"):
                                st.session_state.selected_step = step
                                st.session_state.page_view = "PREVIEW"
                                st.rerun()
            else:
                st.info(get_txt("msg_no_priority"))

    # [탭 2] 워크플로우
    with tab_workflow:
        if st.session_state.page_view != "DETAIL":
            st.subheader(get_txt("wf_title"))
            in_progress = [s for s in steps if s['status'] in ['진행중', '검토중', '자료요청']]
            on_hold = [s for s in steps if s['status'] == '보류']
            completed = [s for s in steps if s['status'] == '완료']
            
            st.markdown(f"### {get_txt('wf_ing')} ({len(in_progress)})")
            if not in_progress: st.caption("No items in progress.")
            for step in in_progress:
                with st.container(border=True):
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        st.markdown(f"**{step['title']}**")
                        st.progress(0.4 if step['status']=='진행중' else 0.7) 
                    with c2:
                        if st.button(get_txt("btn_detail"), key=f"wf_{step['id']}"):
                            st.session_state.selected_step = step
                            st.session_state.page_view = "DETAIL"
                            st.rerun()
            
            if on_hold:
                st.markdown(f"### {get_txt('wf_hold')} ({len(on_hold)})")
                for step in on_hold: st.warning(f"{step['title']}")
            
            if completed:
                st.markdown(f"### {get_txt('wf_done')} ({len(completed)})")
                for step in completed: st.success(f"{step['title']}")

        elif st.session_state.page_view == "DETAIL":
            step = st.session_state.selected_step
            if step:
                if st.button(get_txt("back_prev")):
                    st.session_state.page_view = "WORKFLOW"
                    st.rerun()
                st.title(step['title'])
                c1, c2 = st.columns([1.5, 1])
                with c1:
                    st.markdown(get_txt("step_s1"))
                    st.markdown(get_txt("step_checklist"))

                    if step.get('checklist'):
                        all_chk = True

                        def update_checklist_state(item_id, current_state):
                            new_state = not current_state
                            try:
                                requests.patch(f"{API_URL}/checklist-items/{item_id}", json={"is_checked": new_state})
                            except Exception as e:
                                st.error(f"Error: {e}")

                        for i, item in enumerate(step['checklist']):
                            key = f"chk_{step['id']}_{item['id']}"

                            chk = st.checkbox(
                                item['item_content'],
                                value=item['is_checked'],
                                key=key,
                                on_change=update_checklist_state,
                                args=(item['id'], item['is_checked'])
                            )

                            if not chk: all_chk = False
                    else:
                        st.caption(get_txt("no_checklist"))
                        all_chk = True

                    st.markdown("---")
                    
                    st.markdown(get_txt("step_s2"))
                    if step.get('documents'):
                        for doc in step['documents']:
                            st.success(f"📄 {doc['doc_type']} : {doc['verification_status']}")
                    
                    with st.form(f"up_{step['id']}"):
                        dtype = "CONTRACT" if step['category'] == "HOUSING" else "PASSPORT"
                        
                        # 다국어 라벨 적용
                        label_txt = get_txt("label_file")
                        up = st.file_uploader(label_txt, type=['jpg','pdf'])
                        
                        # 버튼 클릭 시 처리
                        if st.form_submit_button("Submit"):
                            if up:
                                files = {"file": (up.name, up, up.type)}
                                try:
                                    # API 호출
                                    res = requests.post(
                                        f"{API_URL}/users/{st.session_state.user_id}/documents?doc_type={dtype}&step_id={step['id']}", 
                                        files=files
                                    )
                                    
                                    # [성공 시]
                                    if res.status_code == 200:
                                        st.success(get_txt("file_submit_success"))
                                        time.sleep(1)
                                        st.rerun()
                                    # [실패 시 - 에러 메시지 출력]
                                    else:
                                        st.error(f"제출 실패 ({res.status_code}): {res.text}")
                                except Exception as e:
                                    st.error(f"연결 오류: {e}")
                            else:
                                st.warning("파일을 먼저 선택해주세요.") # 파일 없이 버튼 눌렀을 때
                with c2:
                    st.markdown(get_txt("map_nearby"))
                    st.divider()
                    st.markdown(get_txt("help_title"))
                    c_faq, c_exp = st.columns(2)
                    c_faq.button(get_txt("btn_faq"), width="stretch")
                    if c_exp.button(get_txt("btn_ask"), width="stretch"):
                        open_reservation_dialog("Expert")
                
                st.divider()
                if step['status'] != "완료":
                    if all_chk:
                        if st.button(get_txt("btn_finish"), type="primary", width="stretch"):
                            requests.patch(f"{API_URL}/roadmap-steps/{step['id']}", json={"status": "완료"})
                            st.balloons()
                            st.session_state.page_view = "WORKFLOW"
                            st.rerun()
                    else: st.button(get_txt("btn_finish_disable"), disabled=True, width="stretch")

    # [탭 3] 문서 지갑
    with tab_wallet:
        st.subheader(get_txt("wallet_title"))

        with st.expander(get_txt("wallet_add"), expanded=False):
            st.info(get_txt("wallet_info"))
            doc_opts = get_txt("opt_doc") # 리스트 반환
            doc_option = st.radio(get_txt("label_doc_type"), doc_opts, horizontal=True)
            # 인덱스로 타입 추론
            doc_type_code = "PASSPORT" if doc_opts.index(doc_option) == 0 else "CONTRACT"
            
            up = st.file_uploader(get_txt("label_file"), type=['png','jpg','pdf'], key="w_up")
            if up and st.button(get_txt("btn_upload_analyze"), key="w_btn"):
                files = {"file": (up.name, up, up.type)}
                with st.spinner("Analyzing..."):
                    try:
                        res = requests.post(f"{API_URL}/users/{st.session_state.user_id}/documents?doc_type={doc_type_code}", files=files)
                        if res.status_code == 200:
                            new_id = res.json().get("id")
                            requests.post(f"{API_URL}/documents/{new_id}/analyze?user_id={st.session_state.user_id}")
                            st.success(get_txt("msg_upload_success"))
                            time.sleep(1)
                            st.rerun()
                        else: st.error("Upload Failed")
                    except Exception as e:
                        st.error(f"Error: {e}")
        st.divider()

        st.markdown(get_txt("wallet_list"))
        try:
            my_docs = requests.get(f"{API_URL}/users/{st.session_state.user_id}/documents").json()
            if not my_docs: st.info(get_txt("msg_no_docs"))
            else:
                for doc in my_docs:
                    status_key = doc.get('verification_status')

                    stat_map = {
                        "VERIFIED": (get_txt("stat_verified"), "green"),
                        "REVIEW_NEEDED": (get_txt("stat_review"), "orange"),
                        "REJECTED": (get_txt("stat_rejected"), "red"),
                        "UNVERIFIED": (get_txt("stat_unverified"), "gray"),
                        None: (get_txt("stat_review"), "orange")
                    }

                    txt, color = stat_map.get(status_key, (get_txt("stat_review"), "orange"))

                    icon = "🛂" if doc['doc_type'] == "PASSPORT" else "📜"

                    with st.container(border=True):
                        c1, c2, c3 = st.columns([0.5, 3, 1.5])
                        with c1: st.markdown(f"## {icon}")
                        with c2:
                            st.markdown(f"**{doc['doc_type']}**")
                            date_str = doc.get('uploaded_at', '')[:10] if doc.get('uploaded_at') else datetime.today().strftime("%Y-%m-%d")
                            st.caption(f"{date_str}")
                        with c3: st.markdown(f":{color}[**{txt}**]")

                        with st.expander(get_txt("exp_details")):
                            st.caption(f"Path: {doc.get('s3_key', 'N/A')}")
                            import json
                            if doc.get('risk_analysis'):
                                try:
                                    an = json.loads(doc['risk_analysis'])
                                    st.write(f"**Summary:** {an.get('summary')}")
                                    if doc['doc_type'] == "CONTRACT":
                                        st.metric("Risk Score", f"{an.get('risk_score', 0)}")
                                except: pass
        except Exception as e:
            st.error(f"Failed to load documents: {e}")

    # [탭 4] AI 상담
    with tab_chat:
        st.subheader(get_txt("chat_title"))
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.write(m["content"])
                if m.get("action") == "VISA_HELP":
                    st.info("Partner Info")
                    if st.button("Book", key=f"b_{m['content'][:5]}"): open_reservation_dialog("Visa Expert")

        if q := st.chat_input(get_txt("chat_placeholder")):
            st.session_state.messages.append({"role": "user", "content": q})
            st.chat_message("user").write(q)
            try:
                res = requests.post(f"{API_URL}/chat", json={"message": q})
                if res.status_code == 200:
                    data = res.json().get('reply')
                    ai_text = data.get('reply') if isinstance(data, dict) else data
                    ai_act = data.get('action') if isinstance(data, dict) else "NONE"
                    st.chat_message("assistant").write(ai_text)
                    if ai_act == "VISA_HELP":
                        st.info("Recommended Partner")
                        st.button("Book Now", key="now_v")
                    st.session_state.messages.append({"role": "assistant", "content": ai_text, "action": ai_act})
            except Exception as e:
                st.error(f"Error: {e}")

    # ---------------------------------------------------------
    # [Helper] 게시글 카드 렌더링 함수 (수정/삭제/댓글 통합)
    # ---------------------------------------------------------
    def render_post_card(post, current_user_id):
        with st.container(border=True):
            # 1. 헤더 (상태 아이콘 & 제목 & 작성자)
            c1, c2 = st.columns([5, 1])
            with c1:
                icon = "✅" if post.get('is_verified') else "📝"
                if post.get('result_tag') == "SUCCESS": icon = "🟢 [승인]"
                elif post.get('result_tag') == "FAIL": icon = "🔴 [반려]"
                
                st.markdown(f"### {icon} {post['title']}")
                st.caption(f"User: {post['author_id']} | Date: {post.get('created_at', '')[:10]}")
            
            # 2. 본인 글 수정/삭제 버튼 (작성자만 보임)
            if current_user_id == post['author_id']:
                with c2:
                    # 수정 기능 (Popover 사용)
                    with st.popover(get_txt("btn_edit")):
                        with st.form(key=f"edit_form_{post['id']}"):
                            new_title = st.text_input(get_txt("label_edit_title"), value=post['title'])
                            new_content = st.text_area(get_txt("label_edit_content"), value=post['content'])
                            if st.form_submit_button(get_txt("btn_update")):
                                try:
                                    requests.put(f"{API_URL}/community/posts/{post['id']}?user_id={current_user_id}", 
                                                 json={"title": new_title, "content": new_content})
                                    st.success(get_txt("msg_update_success"))
                                    time.sleep(0.5)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Update Failed: {e}")
                    
                    # 삭제 기능
                    if st.button(get_txt("btn_delete"), key=f"del_{post['id']}"):
                        try:
                            requests.delete(f"{API_URL}/community/posts/{post['id']}?user_id={current_user_id}")
                            st.toast(get_txt("msg_delete_confirm"))
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Delete Failed: {e}")

            # 3. 본문 내용
            st.write(post['content'])
            st.divider()
            
            # 4. 댓글 영역
            comments = post.get('comments', [])
            st.caption(get_txt("header_comments").format(count=len(comments)))
            
            if comments:
                for c in comments:
                    st.markdown(f"**User {c['author_id']}**: {c['content']}")
            else:
                st.caption(get_txt("msg_no_comments"))
            
            # 댓글 작성 폼
            with st.form(key=f"comment_form_{post['id']}", clear_on_submit=True):
                c_col1, c_col2 = st.columns([4, 1])
                new_comment = c_col1.text_input(get_txt("label_comment"), label_visibility="collapsed")
                if c_col2.form_submit_button(get_txt("btn_add_comment")):
                    if new_comment:
                        try:
                            requests.post(f"{API_URL}/community/posts/{post['id']}/comments?user_id={current_user_id}", 
                                          json={"content": new_comment})
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

    # [탭 5] 커뮤니티
    with tab_community:
        st.subheader(get_txt("com_title"))

        with st.expander(get_txt("com_write")):
            with st.form("new_post"):
                c1, c2 = st.columns(2)
                # 다국어 옵션 처리
                board_opts = get_txt("opt_board")
                cat_type = c1.selectbox(get_txt("label_board"), board_opts)
                v_type = c2.selectbox("Visa", ["D-2", "D-4"])

                res_tag = "NONE"
                if cat_type == board_opts[0]:
                    res_tag_display = st.radio("Result", ["Success (승인)", "Fail (반려)"], horizontal=True)
                    res_tag = "SUCCESS" if "Success" in res_tag_display else "FAIL"

                title = st.text_input(get_txt("label_title"))
                content = st.text_area(get_txt("label_content"))

                if st.form_submit_button(get_txt("btn_register")):
                    # 인덱스로 카테고리 매핑
                    cat_map = ["REVIEW", "INFO", "QNA"]
                    cat_code = cat_map[board_opts.index(cat_type)]
                    
                    payload = {
                        "title": title,
                        "content": content,
                        "visa_type": v_type,
                        "category": cat_code,
                        "result_tag": res_tag
                    }
                    try:
                        requests.post(f"{API_URL}/community/posts?user_id={st.session_state.user_id}", json=payload)
                        st.success(get_txt("msg_reg_success"))
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to post: {e}")
        
        st.divider()

        t1, t2, t3 = st.tabs(get_txt("tabs_com"))

        with t1: # Review
            try:
                posts = requests.get(f"{API_URL}/community/posts?category=REVIEW").json()
                if not posts: st.info(get_txt("msg_no_posts"))
                else:
                    for p in posts:
                        render_post_card(p, st.session_state.user_id)
            except Exception as e: st.error(f"Load Error: {e}")

        with t2: # Info
            show_v = st.toggle(get_txt("toggle_verified"))
            url = f"{API_URL}/community/posts?category=INFO"
            if show_v: url += "&verified_only=true"
            try:
                posts = requests.get(url).json()
                if not posts: st.info(get_txt("msg_no_posts"))
                else:
                    for p in posts:
                        render_post_card(p, st.session_state.user_id)
            except Exception as e: st.error(f"Load Error: {e}")

        with t3: # QnA
            try:
                posts = requests.get(f"{API_URL}/community/posts?category=QNA").json()
                if not posts: st.info(get_txt("msg_no_posts"))
                else:
                    for p in posts:
                        render_post_card(p, st.session_state.user_id)
            except Exception as e: st.error(f"Load Error: {e}")

    # [탭 6] 지도
    with tab_map:
        st.subheader(get_txt("map_title"))
        st.markdown(get_txt("label_standard").format(univ=my_univ))
        
        agency_opts = get_txt("opt_agency")
        opt = st.radio("Category", agency_opts, horizontal=True)
        # 인덱스로 카테고리 매핑
        cat_map = ["BANK", "OFFICE", "IMMIGRATION"]
        cat_code = cat_map[agency_opts.index(opt)]
        
        # [복구 확인 완료] 대학교별 중심 좌표 데이터
        univ_coords = {
            "연세대학교 (Sinchon)": [37.565784, 126.938572],
            "서울대학교 (Gwanak)": [37.459882, 126.951905],
            "고려대학교 (Anam)": [37.589400, 127.032300],
            "한양대학교 (Seoul)": [37.557232, 127.045322]
        }
        # 중심점 계산 로직
        center = univ_coords.get(my_univ, [37.5665, 126.9780])

        try:
            res = requests.get(f"{API_URL}/agencies?category={cat_code}")
            if res.status_code == 200:
                data = res.json()
                if data:
                    st.map(pd.DataFrame(data), latitude='lat', longitude='lon', size=200, color='#0044ff')
                    st.markdown(get_txt("map_rec").format(univ=my_univ))
                    
                    # [복구 확인 완료] 거리 계산 필터링
                    nearby = [x for x in data if abs(x['lat']-center[0])<0.03 and abs(x['lon']-center[1])<0.03]
                    
                    if nearby:
                        for place in nearby:
                            with st.container(border=True):
                                st.markdown(f"**{place['name']}**")
                                st.caption(f"📍 {place['address']}")
                                st.button(get_txt("btn_nav"), key=f"nav_{place['id']}")
                    else: st.info("No data nearby.")
        except: pass

# ==========================================
# 4. 앱 실행 분기
# ==========================================
try:
    if st.session_state.access_token is None:
        login_page()
    elif st.session_state.user_id is None:
        headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
        try:
            res = requests.get(f"{API_URL}/users/me", headers=headers)
            if res.status_code == 200:
                u = res.json()
                st.session_state.user_id = u['id']
                st.session_state.user_name = u['full_name']
                st.session_state.visa_type = u['visa_type']
                st.session_state.is_admin = u.get("is_admin", False)
                st.rerun()
            else:
                st.session_state.access_token = None
                st.rerun()
        except Exception:
            st.session_state.access_token = None
            st.rerun()
    elif st.session_state.is_admin or st.session_state.visa_type is not None:
        main_dashboard()
    else:
        setup_profile_page()

except Exception as e:
    # 앱이 멈추지 않고 에러 메시지를 보여주며 복구할 수 있게 함
    st.error(f"알 수 없는 오류가 발생했습니다: {e}")
    # 세션이 꼬였을 때를 대비한 탈출 버튼
    if st.button("강제 로그아웃 (오류 해결용)"):
        st.session_state.clear()
        st.rerun()