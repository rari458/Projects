import streamlit as st
import requests
from datetime import datetime, date
import pandas as pd
import time

# 페이지 설정
st.set_page_config(page_title="Settlo", layout="wide", page_icon="🌏")

# API 주소
API_URL = "https://settlo-647487045104.asia-northeast3.run.app"

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

# --- [NEW] 화면 상태 관리 초기화 ---
if "page_view" not in st.session_state:
    st.session_state.page_view = "HOME" # HOME, PREVIEW, DETAIL
if "selected_step" not in st.session_state:
    st.session_state.selected_step = None
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# ==========================================
# 1. 로그인 / 회원가입 화면
# ==========================================
def login_page():
    st.title("🌏 Settlo")
    st.subheader("외국인 유학생을 위한 AI 정착 플랫폼")

    tab1, tab2 = st.tabs(["🔑 로그인", "✨ 회원가입"])

    with tab1:
        with st.container(border=True):
            login_id = st.text_input("아이디 (ID)", key="login_id")
            login_pw = st.text_input("비밀번호 (Password)", type="password", key="login_pw")
            
            if st.button("로그인 하기", width="stretch"):
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
                        st.success("로그인 성공!")
                        st.rerun()
                    else:
                        st.error("아이디 또는 비밀번호가 잘못되었습니다.")
                except Exception as e:
                    st.error(f"서버 연결 실패: {e}")

    with tab2:
        with st.container(border=True):
            st.markdown("### 가입 정보 입력")
            new_id = st.text_input("아이디 생성", key="new_id")
            new_pw = st.text_input("비밀번호 설정", type="password", key="new_pw")
            new_email = st.text_input("이메일 주소", key="new_email")
            new_name = st.text_input("이름 (Full Name)", key="new_name")
            
            if st.button("가입하기", width="stretch"):
                if new_id and new_pw and new_email and new_name:
                    payload = {"username": new_id, "password": new_pw, "email": new_email, "full_name": new_name}
                    try:
                        res = requests.post(f"{API_URL}/users/signup", json=payload)
                        if res.status_code == 200:
                            st.success("가입되었습니다! 로그인 탭에서 로그인해주세요.")
                        elif res.status_code == 400:
                            st.error("이미 존재하는 아이디입니다.")
                        else:
                            st.error(f"가입 실패: {res.text}")
                    except Exception as e:
                        st.error(f"오류: {e}")
                else:
                    st.warning("모든 정보를 입력해주세요.")

# ==========================================
# 2. 초기 정보 설정
# ==========================================
def setup_profile_page():
    st.title("👋 환영합니다!")
    st.info("맞춤형 서비스를 위해 초기 정보를 설정해주세요.")
    
    with st.form("setup_form"):
        col1, col2 = st.columns(2)
        with col1:
            nationality = st.text_input("국적", placeholder="")
            entry_date = st.date_input("입국일", date.today())
        with col2:
            visa = st.selectbox("비자 타입", ["D-2", "D-4"])
        
        if st.form_submit_button("설정 저장 및 시작하기"):
            if st.session_state.user_id:
                payload = {"nationality": nationality, "visa_type": visa, "entry_date": str(entry_date)}
                try:
                    res = requests.patch(f"{API_URL}/users/{st.session_state.user_id}/visa", json=payload)
                    if res.status_code == 200:
                        st.session_state.visa_type = visa
                        st.success("설정 완료!")
                        st.rerun()
                    else:
                        st.error("정보 저장 실패")
                except Exception as e:
                    if "Rerun" in str(type(e)): raise e
                    st.error(f"오류: {e}")

# ==========================================
# 3. 메인 대시보드
# ==========================================
def main_dashboard():
    if st.session_state.get("is_admin", False):
        with st.sidebar:
            st.header("🔒 Admin Mode")
            if st.button("로그아웃", width="stretch"):
                for key in list(st.session_state.keys()): del st.session_state[key]
                st.rerun()
        
        st.title("🔒 관리자(Admin) 대시보드")
        st.info(f"관리자 계정({st.session_state.user_name})으로 접속했습니다.")
        
        ad_tab1, ad_tab2, ad_tab3 = st.tabs(["📄 문서 검토 대기", "📅 예약 현황", "📢 정보글 검증"])
        
        # 1. 문서 검토
        with ad_tab1:
            try:
                pending_docs = requests.get(f"{API_URL}/admin/pending-documents").json()
                if not pending_docs: st.success("대기 중인 문서가 없습니다.")
                else:
                    for doc in pending_docs:
                        with st.container(border=True):
                            c1, c2, c3 = st.columns([2, 2, 1])
                            c1.markdown(f"**Doc ID: {doc['id']}** ({doc['doc_type']})")
                            c1.caption(f"User: {doc['user_id']} | Date: {doc['uploaded_at'][:10]}")
                            
                            # AI 분석 요약 표시
                            import json
                            try:
                                summary = json.loads(doc['risk_analysis']).get('summary', '-')
                                c2.info(f"AI: {summary}")
                            except: c2.caption("AI 데이터 없음")
                            
                            with c3:
                                if st.button("✅ 승인", key=f"ok_{doc['id']}", use_container_width=True):
                                    requests.patch(f"{API_URL}/documents/{doc['id']}/status", json={"status": "VERIFIED"})
                                    st.rerun()
                                if st.button("🚫 반려", key=f"no_{doc['id']}", use_container_width=True):
                                    requests.patch(f"{API_URL}/documents/{doc['id']}/status", json={"status": "REJECTED"})
                                    st.rerun()
            except: st.error("문서 로드 실패")

        # 2. 예약 현황
        with ad_tab2:
            try:
                res_list = requests.get(f"{API_URL}/admin/reservations").json()
                if res_list:
                    df = pd.DataFrame(res_list)[['partner_name', 'reservation_date', 'reservation_time', 'user_id', 'memo']]
                    df.columns = ['담당자', '날짜', '시간', '유저ID', '요청메모']
                    st.dataframe(df, use_container_width=True)
                else: st.info("예약 내역 없음")
            except: st.error("예약 로드 실패")

        # 3. 정보글 검증
        with ad_tab3:
            try:
                posts = requests.get(f"{API_URL}/community/posts?category=INFO").json()
                unverified = [p for p in posts if not p['is_verified']]
                if not unverified: st.success("검증 대기 글이 없습니다.")
                else:
                    for p in unverified:
                        with st.expander(f"{p['title']} (User: {p['author_id']})"):
                            st.write(p['content'])
                            if st.button("🏅 검증 마크 부여", key=f"v_post_{p['id']}"):
                                requests.patch(f"{API_URL}/community/posts/{p['id']}/verify", json={"is_verified": True})
                                st.rerun()
            except: st.error("글 로드 실패")

        return # [중요] 관리자면 여기서 함수 종료! (아래 학생 화면 실행 안 함)
    # --- [NEW] 예약 모달 함수 정의 ---
    @st.dialog("📅 전문가 상담 예약")
    def open_reservation_dialog(partner_name):
        st.write(f"**'{partner_name}'**님과 상담을 예약합니다.")
        with st.form("res_form"):
            d = st.date_input("날짜 선택", date.today())
            t = st.time_input("시간 선택", datetime.now().time())
            memo = st.text_area("요청 사항 (선택)", placeholder="예: 비자 연장 관련 문의입니다.")
            if st.form_submit_button("예약 확정하기"):
                payload = {
                    "partner_name": partner_name,
                    "reservation_date": str(d),
                    "reservation_time": str(t),
                    "memo": memo
                }
                try:
                    res = requests.post(f"{API_URL}/reservations?user_id={st.session_state.user_id}", json=payload)
                    if res.status_code == 200:
                        st.success("예약이 확정되었습니다! 🎉")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("예약 실패")
                except Exception as e:
                    st.error(f"오류: {e}")

    # --- 사이드바 ---
    with st.sidebar:
        st.header(f"반가워요, {st.session_state.user_name}님! 👋")
        
        st.markdown("### 🏫 내 정착 정보")
        univ_list = ["연세대학교 (Sinchon)", "서울대학교 (Gwanak)", "고려대학교 (Anam)", "한양대학교 (Seoul)"]
        my_univ = st.selectbox("소속 대학교", univ_list, index=0)
        
        region_list = ["서대문구 (Seodaemun)", "관악구 (Gwanak)", "성북구 (Seongbuk)", "마포구 (Mapo)"]
        my_region = st.selectbox("거주 지역", region_list, index=0)

        st.divider()
        st.markdown("### 🔔 알림 센터")
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
                                    alerts.append(f"🚨 **{s['title']}** 마감 D-{days_left}!")
                                elif days_left < 0:
                                    alerts.append(f"🔥 **{s['title']}** 기한 초과!")
                        if alerts:
                            for a in alerts: st.markdown(a)
                        else:
                            st.caption("예정된 급한 일정이 없습니다. ☕")
                except: st.caption("로딩 중...")
        
        st.divider()
        st.markdown("### ⚙️ 내 체류 정보")
        visa_options = ["D-2", "D-4"]
        current_visa = st.session_state.get('visa_type', 'D-2')
        try: default_ix = visa_options.index(current_visa)
        except: default_ix = 0
        selected_visa = st.selectbox("비자 타입", visa_options, index=default_ix)
        if selected_visa != current_visa:
            st.warning("비자 변경 시 로드맵이 초기화됩니다.")
            if st.button("변경사항 저장", width="stretch"):
                try:
                    payload = {"visa_type": selected_visa}
                    requests.patch(f"{API_URL}/users/{st.session_state.user_id}/visa", json=payload)
                    st.session_state.visa_type = selected_visa
                    st.success("변경 완료!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e: st.error(f"오류: {e}")

        st.divider()
        if st.button("로그아웃", width="stretch"):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    # --- 메인 탭 구성 (PDF 구조 반영) ---
    tab_home, tab_workflow, tab_wallet, tab_chat, tab_community, tab_map = st.tabs(
        ["🏠 홈", "🛤️ 워크플로우", "📂 문서 지갑", "💬 AI 상담", "🗣️ 커뮤니티", "📍 기관 찾기"]
    )

    # 로드맵 데이터 가져오기 (공통)
    steps = []
    if st.session_state.user_id:
        try:
            res = requests.get(f"{API_URL}/users/{st.session_state.user_id}/roadmap")
            if res.status_code == 200:
                steps = res.json().get('steps', [])
        except: pass

    # =========================================================================
    # [탭 1] 홈 화면 (탐색 & 미리보기)
    # =========================================================================
    with tab_home:
        # [화면 A] 기본 홈 화면
        if st.session_state.page_view == "HOME":
            st.subheader(f"안녕하세요, {st.session_state.user_name}님!")
            st.markdown("한국 정착을 위한 필수 과정을 안내해 드립니다.")
            
            # 1. 상단 아이콘
            st.markdown("##### 🏛️ 기관별 업무 탐색")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.button("🏫\n학교", use_container_width=True)
            c2.button("🏢\n행정", use_container_width=True)
            c3.button("🏦\n은행", use_container_width=True)
            c4.button("📡\n통신", use_container_width=True)
            c5.button("🏠\n주거", use_container_width=True)

            st.divider()

            # 2. 우선 항목 리스트 (대기 중인 항목)
            st.markdown("##### 🔥 우선 해결해야 할 항목")
            waiting_steps = [s for s in steps if s['status'] == '대기']
            
            if waiting_steps:
                for step in waiting_steps:
                    with st.container(border=True):
                        col_txt, col_btn = st.columns([4, 1])
                        with col_txt:
                            st.markdown(f"**{step['title']}**")
                            st.caption(f"{step['description'][:40]}...")
                        with col_btn:
                            if st.button("보기", key=f"pre_{step['id']}"):
                                st.session_state.selected_step = step
                                st.session_state.page_view = "PREVIEW"
                                st.rerun()
            else:
                st.info("현재 대기 중인 우선 항목이 없습니다! 워크플로우 탭을 확인해보세요.")

        # [화면 B] 항목 상세 미리보기 (Preview)
        elif st.session_state.page_view == "PREVIEW":
            step = st.session_state.selected_step
            if step:
                if st.button("← 홈으로 돌아가기"):
                    st.session_state.page_view = "HOME"
                    st.rerun()
                
                st.title(step['title'])
                st.markdown(f"**{step['description']}**")
                
                st.info(f"💡 유학생의 82%가 입국 후 1주 이내에 완료하는 절차입니다.")
                
                c1, c2 = st.columns(2)
                c1.metric("평균 소요 시간", "1~3일") 
                c2.metric("방문 필요 여부", "최초 1회 방문")
                
                st.markdown("### ■ 이런 경우에 필요해요")
                st.write("- 한국에서의 공식 신분 증명이 필요할 때")
                st.write("- 은행 계좌 개설 및 휴대폰 개통 시")
                
                st.divider()
                
                if st.button("🚀 바로 시작하기 (워크플로우에 추가)", type="primary", use_container_width=True):
                    try:
                        requests.patch(f"{API_URL}/roadmap-steps/{step['id']}", json={"status": "진행중"})
                        st.toast(f"{step['title']} 항목이 시작되었습니다!")
                        time.sleep(1)
                        st.session_state.page_view = "HOME" 
                        st.rerun()
                    except Exception as e: st.error(f"오류: {e}")

    # =========================================================================
    # [탭 2] 워크플로우 (나의 진행 현황)
    # =========================================================================
    with tab_workflow:
        # [화면 C] 워크플로우 리스트
        if st.session_state.page_view != "DETAIL":
            st.subheader("나의 워크플로우")
            
            in_progress = [s for s in steps if s['status'] in ['진행중', '검토중', '자료요청']]
            on_hold = [s for s in steps if s['status'] == '보류']
            completed = [s for s in steps if s['status'] == '완료']
            
            # 1. 진행중
            st.markdown(f"### 🔵 진행중 ({len(in_progress)})")
            if not in_progress: st.caption("진행 중인 항목이 없습니다.")
            for step in in_progress:
                with st.container(border=True):
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        st.markdown(f"**{step['title']}**")
                        st.caption(f"상태: {step['status']}")
                        st.progress(0.4 if step['status']=='진행중' else 0.7) 
                    with c2:
                        if st.button("상세", key=f"wf_go_{step['id']}"):
                            st.session_state.selected_step = step
                            st.session_state.page_view = "DETAIL"
                            st.rerun()
            
            # 2. 보류
            if on_hold:
                st.markdown(f"### 🟡 보류 ({len(on_hold)})")
                for step in on_hold:
                    st.warning(f"{step['title']} (사유: 서류 미비)")

            # 3. 완료
            if completed:
                st.markdown(f"### 🟢 완료 ({len(completed)})")
                for step in completed:
                    with st.expander(f"✅ {step['title']}"):
                        st.write("완료된 항목입니다.")

        # [화면 D] 특정 항목 상세 실행 (Detail)
        elif st.session_state.page_view == "DETAIL":
            step = st.session_state.selected_step
            if step:
                if st.button("← 목록으로"):
                    st.session_state.page_view = "WORKFLOW"
                    st.rerun()
                
                st.title(step['title'])
                st.progress(0.5)
                
                c_left, c_right = st.columns([1.5, 1])
                
                with c_left:
                    st.markdown("#### STEP 1. 방문 및 준비")
                    st.info(f"⏱️ 예상 소요: 30~60분  |  💰 예상 비용: 무료")
                    
                    st.markdown("**☑ 방문 전 준비물 (Checklist)**")
                    if step.get('checklist'):
                        all_chk = True
                        for item in step['checklist']:
                            is_checked = st.checkbox(item['item_content'], value=item['is_checked'], key=f"d_chk_{item['id']}")
                            if not is_checked: all_chk = False
                            if is_checked != item['is_checked']:
                                requests.patch(f"{API_URL}/checklist-items/{item['id']}", json={"is_checked": is_checked})
                                st.rerun()
                    else: 
                        st.caption("체크리스트 없음")
                        all_chk = True

                    st.markdown("---")
                    
                    st.markdown("#### STEP 2. 문서 제출 및 검토")
                    if step.get('documents'):
                        for doc in step['documents']:
                            status_txt = "제출 완료" if doc['verification_status'] != 'UNVERIFIED' else "검토 중"
                            st.success(f"📄 {doc['doc_type']} : **{status_txt}**")
                    
                    with st.form(f"detail_up_{step['id']}"):
                        dtype = "CONTRACT" if step['category'] == "HOUSING" else "PASSPORT"
                        up = st.file_uploader("파일 첨부", type=['jpg','pdf'])
                        if st.form_submit_button("문서 제출하기") and up:
                            files = {"file": (up.name, up, up.type)}
                            res = requests.post(f"{API_URL}/users/{st.session_state.user_id}/documents?doc_type={dtype}&step_id={step['id']}", files=files)
                            if res.status_code == 200:
                                st.success("제출되었습니다!")
                                time.sleep(1)
                                st.rerun()

                with c_right:
                    st.markdown("#### 📍 내 주변 방문 기관")
                    try:
                        cat_map = {"ENTRY": "OFFICE", "HOUSING": "OFFICE", "VISA": "IMMIGRATION", "BANK": "BANK"}
                        cat = cat_map.get(step['category'], "ALL")
                        agencies = requests.get(f"{API_URL}/agencies?category={cat}").json()
                        if agencies:
                            st.map(pd.DataFrame(agencies), latitude='lat', longitude='lon', size=20, color='#0044ff')
                            st.caption(f"추천: {agencies[0]['name']}")
                    except: st.caption("지도 로딩 실패")

                    st.divider()
                    
                    st.markdown("#### 💬 도움말")
                    c_faq, c_exp = st.columns(2)
                    c_faq.button("FAQ\n보기", use_container_width=True)
                    if c_exp.button("전문가\n질문", use_container_width=True):
                        open_reservation_dialog("전문가 매칭")

                st.divider()
                if step['status'] != "완료":
                    if all_chk:
                        if st.button("🎉 이 단계 완료하기 (Next Step)", type="primary", use_container_width=True):
                            requests.patch(f"{API_URL}/roadmap-steps/{step['id']}", json={"status": "완료"})
                            st.balloons()
                            st.session_state.page_view = "WORKFLOW"
                            st.rerun()
                    else:
                        st.button("완료 (체크리스트 확인 필요)", disabled=True, use_container_width=True)

    # =========================================================================
    # [탭 3] 문서 지갑 (업그레이드: 목록 조회 + 업로드)
    # =========================================================================
    with tab_wallet:
        st.subheader("📂 내 문서 보관함")

        # 1. 새 문서 추가 (공간 절약을 위해 접어둠)
        with st.expander("➕ 새 문서 등록 및 분석하기", expanded=False):
            st.info("여권이나 계약서를 업로드하면 AI가 진위 여부와 독소 조항을 분석합니다.")
            doc_option = st.radio("문서 종류", ["🛂 여권/등록증", "📜 임대차/근로 계약서"], horizontal=True)
            doc_type_code = "PASSPORT" if "여권" in doc_option else "CONTRACT"
            
            up_file = st.file_uploader("파일 선택", type=['png', 'jpg', 'pdf'], key="wallet_up")
            
            if up_file and st.button("업로드 및 분석 시작", key="wallet_btn"):
                files = {"file": (up_file.name, up_file, up_file.type)}
                with st.spinner("AI가 문서를 분석 중입니다..."):
                    try:
                        res = requests.post(f"{API_URL}/users/{st.session_state.user_id}/documents?doc_type={doc_type_code}", files=files)
                        if res.status_code == 200:
                            new_doc_id = res.json().get("id")
                            # 분석 요청
                            requests.post(f"{API_URL}/documents/{new_doc_id}/analyze?user_id={st.session_state.user_id}")
                            st.success("등록 및 분석 완료! 아래 목록에서 확인하세요.")
                            time.sleep(1)
                            st.rerun() # 목록 갱신을 위해 리로딩
                        else:
                            st.error("업로드 실패")
                    except Exception as e:
                        st.error(f"오류: {e}")

        st.divider()

        # 2. 저장된 문서 목록 조회
        st.markdown("### 📜 저장된 문서")
        try:
            # Backend에서 문서 목록 가져오기
            my_docs = requests.get(f"{API_URL}/users/{st.session_state.user_id}/documents").json()
            
            if not my_docs:
                st.info("아직 저장된 문서가 없습니다. 위에서 문서를 추가해보세요!")
            else:
                for doc in my_docs:
                    # 상태별 아이콘 및 색상 매핑
                    status_map = {
                        "VERIFIED": ("✅ 승인됨", "green"),
                        "REVIEW_NEEDED": ("🟡 검토중", "orange"),
                        "REJECTED": ("🚫 반려됨", "red"),
                        "UNVERIFIED": ("⏳ 미인증", "gray")
                    }
                    # 기본값 처리
                    stat_text, stat_color = status_map.get(doc.get('verification_status', 'UNVERIFIED'), ("미확인", "gray"))
                    
                    icon = "🛂" if doc['doc_type'] == "PASSPORT" else "📜"
                    
                    # 문서 카드 UI
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([0.5, 3, 1.5])
                        with c1: st.markdown(f"## {icon}")
                        with c2:
                            st.markdown(f"**{doc['doc_type']}**")
                            # 날짜 포맷팅 (문자열 슬라이싱 활용)
                            uploaded_date = doc['uploaded_at'][:10] if 'uploaded_at' in doc else "날짜없음"
                            st.caption(f"등록일: {uploaded_date}")
                        with c3:
                            st.markdown(f":{stat_color}[**{stat_text}**]")
                        
                        # 상세 내용 (AI 분석 결과 등)
                        with st.expander("상세 보기"):
                            # 저장된 파일 경로 (실제 서비스에선 다운로드 링크 제공)
                            st.caption(f"파일 경로: {doc.get('s3_key', 'N/A')}")
                            
                            # AI 분석 결과 파싱 및 표시
                            import json
                            if doc.get('risk_analysis'):
                                try:
                                    analysis = json.loads(doc['risk_analysis'])
                                    
                                    # 계약서일 경우
                                    if doc['doc_type'] == "CONTRACT":
                                        score = int(analysis.get('risk_score', 0))
                                        st.metric("위험도 점수", f"{score}점")
                                        st.write(f"**요약:** {analysis.get('summary')}")
                                        if analysis.get('risk_factors'):
                                            st.error("발견된 위험 조항:")
                                            for risk in analysis['risk_factors']:
                                                st.markdown(f"- {risk['reason']}")
                                    
                                    # 여권/신분증일 경우
                                    else:
                                        st.write(f"**요약:** {analysis.get('summary')}")
                                        if analysis.get('expiry_date'):
                                            st.warning(f"만료일: {analysis['expiry_date']}")
                                except:
                                    st.caption("분석 데이터 형식이 올바르지 않습니다.")
                            else:
                                st.info("AI 분석 데이터가 없습니다.")

        except Exception as e:
            st.error(f"목록을 불러오는 중 오류가 발생했습니다: {e}")

    # =========================================================================
    # [탭 4] AI 상담사 (통합 완료)
    # =========================================================================
    with tab_chat:
        st.subheader("💬 AI 컨시어지")
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.write(m["content"])
                action = m.get("action")
                if action == "FIND_HOUSE":
                    st.info("🏠 추천 파트너")
                    c1,c2 = st.columns(2)
                    c1.button("📞 연결", key=f"h1_{m['content'][:5]}")
                    c2.button("📞 예약", key=f"h2_{m['content'][:5]}")
                elif action == "VISA_HELP":
                    st.info("📅 행정사 파트너")
                    c1,c2 = st.columns(2)
                    if c1.button("예약 (김정수)", key=f"v1_{m['content'][:5]}"): open_reservation_dialog("김정수 행정사")
                    if c2.button("예약 (Global)", key=f"v2_{m['content'][:5]}"): open_reservation_dialog("Global Visa Lab")

        if q := st.chat_input("질문하세요"):
            st.session_state.messages.append({"role": "user", "content": q})
            st.chat_message("user").write(q)
            try:
                res = requests.post(f"{API_URL}/chat", json={"message": q})
                if res.status_code == 200:
                    data = res.json().get('reply')
                    ai_text = data.get('reply') if isinstance(data, dict) else data
                    ai_action = data.get('action') if isinstance(data, dict) else "NONE"
                    
                    st.chat_message("assistant").write(ai_text)
                    if ai_action == "FIND_HOUSE":
                        st.info("🏠 추천 파트너")
                        st.columns(2)[0].button("📞 연결", key="now_h1")
                    elif ai_action == "VISA_HELP":
                        st.info("📅 행정사 파트너")
                        st.columns(2)[0].button("예약", key="now_v1")
                        
                    st.session_state.messages.append({"role": "assistant", "content": ai_text, "action": ai_action})
            except: st.error("응답 실패")

    # =========================================================================
    # [탭 5] 커뮤니티 (리뉴얼: 후기 / 정보 / Q&A 분리)
    # =========================================================================
    with tab_community:
        st.subheader("🗣️ 커뮤니티")
        
        # 1. 글쓰기 영역 (공통)
        with st.expander("📝 새 글 작성하기", expanded=False):
            with st.form("new_post_form"):
                c1, c2 = st.columns([1, 1])
                # 카테고리 선택
                cat_type = c1.selectbox("게시판 선택", ["후기 게시판", "정보 공유", "Q&A (질문)"])
                v_type = c2.selectbox("비자 타입", ["D-2", "D-4"])
                
                # 후기 게시판일 경우에만 태그 선택
                res_tag = "NONE"
                if cat_type == "후기 게시판":
                    res_tag_kr = st.radio("결과", ["✅ 승인 (Success)", "🚫 반려 (Fail)"], horizontal=True)
                    res_tag = "SUCCESS" if "승인" in res_tag_kr else "FAIL"
                
                title = st.text_input("제목")
                content = st.text_area("내용")
                
                if st.form_submit_button("등록"):
                    # 카테고리 매핑
                    cat_map = {"후기 게시판": "REVIEW", "정보 공유": "INFO", "Q&A (질문)": "QNA"}
                    
                    payload = {
                        "title": title, 
                        "content": content, 
                        "visa_type": v_type, 
                        "category": cat_map[cat_type],
                        "result_tag": res_tag
                    }
                    try:
                        requests.post(f"{API_URL}/community/posts?user_id={st.session_state.user_id}", json=payload)
                        st.success("등록되었습니다!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"등록 실패: {e}")

        st.divider()

        # 2. 게시판 탭 분리
        sub_tab1, sub_tab2, sub_tab3 = st.tabs(["📢 승인/반려 후기", "💡 정보 게시판", "❓ Q&A"])

        # (1) 승인/반려 후기 (카드형)
        with sub_tab1:
            # 필터
            filter_visa = st.radio("비자 필터", ["전체", "D-2", "D-4"], horizontal=True, key="f1")
            v_param = filter_visa if filter_visa != "전체" else "ALL"
            
            try:
                # API 호출: category=REVIEW
                posts = requests.get(f"{API_URL}/community/posts?visa_filter={v_param}&category=REVIEW").json()
                if not posts:
                    st.info("등록된 후기가 없습니다.")
                else:
                    # 카드 형태로 표시
                    for p in posts:
                        with st.container(border=True):
                            # 헤더 색상 구분
                            color = "green" if p['result_tag'] == "SUCCESS" else "red"
                            status_icon = "✅ 승인" if p['result_tag'] == "SUCCESS" else "🚫 반려"
                            
                            c_head, c_body = st.columns([1, 4])
                            with c_head:
                                st.markdown(f":{color}-background[**{status_icon}**]")
                                st.caption(p['visa_type'])
                            with c_body:
                                st.markdown(f"**{p['title']}**")
                                st.write(p['content'])
                                if p.get('comments'):
                                    st.divider()
                                    for c in p['comments']:
                                        st.caption(f"💬 {c['content']}")
                                # 간단 댓글 달기
                                with st.popover("댓글 달기"):
                                    c_txt = st.text_input("내용", key=f"c_rev_{p['id']}")
                                    if st.button("등록", key=f"b_rev_{p['id']}"):
                                        requests.post(f"{API_URL}/community/posts/{p['id']}/comments?user_id={st.session_state.user_id}", json={"content": c_txt})
                                        st.rerun()
            except: st.error("로딩 실패")

        # (2) 정보 게시판 (리스트형 + 검증 필터)
        with sub_tab2:
            col_f1, col_f2 = st.columns([3, 1])
            with col_f1:
                st.caption("유용한 꿀팁과 정보를 공유하는 공간입니다.")
            with col_f2:
                # [핵심 기능] 검증글만 보기 토글
                show_verified = st.toggle("✅ 검증된 글만 보기")
            
            try:
                # API 호출: category=INFO, verified_only 적용
                url = f"{API_URL}/community/posts?category=INFO"
                if show_verified: url += "&verified_only=true"
                
                posts = requests.get(url).json()
                
                if not posts:
                    st.info("조건에 맞는 정보글이 없습니다.")
                else:
                    for p in posts:
                        # 검증된 글이면 앞에 아이콘 표시
                        icon = "✅ [검증] " if p['is_verified'] else ""
                        with st.expander(f"{icon}{p['title']}"):
                            st.caption(f"작성자 ID: {p['author_id']} | 비자: {p['visa_type']}")
                            st.write(p['content'])
                            
                            # 댓글 표시
                            if p.get('comments'):
                                st.markdown("---")
                                for c in p['comments']: st.caption(f"└ {c['content']}")
                            
                            # 댓글 입력
                            with st.form(f"info_cmt_{p['id']}"):
                                r1, r2 = st.columns([4, 1])
                                c_txt = r1.text_input("댓글", label_visibility="collapsed")
                                if r2.form_submit_button("등록"):
                                    requests.post(f"{API_URL}/community/posts/{p['id']}/comments?user_id={st.session_state.user_id}", json={"content": c_txt})
                                    st.rerun()
            except: st.error("로딩 실패")

        # (3) Q&A 게시판 (자유 질문)
        with sub_tab3:
            st.caption("자유롭게 질문하고 답변을 주고받으세요.")
            try:
                posts = requests.get(f"{API_URL}/community/posts?category=QNA").json()
                if not posts: st.info("아직 질문이 없습니다.")
                else:
                    for p in posts:
                        with st.container(border=True):
                            st.markdown(f"❓ **{p['title']}**")
                            st.write(p['content'])
                            
                            # 답변(댓글) 영역
                            if p.get('comments'):
                                st.markdown("---")
                                for c in p['comments']:
                                    st.info(f"└ 🗣️ {c['content']}")
                            else:
                                st.caption("아직 답변이 없습니다.")
                            
                            with st.form(f"qna_cmt_{p['id']}"):
                                r1, r2 = st.columns([4, 1])
                                c_txt = r1.text_input("답변하기", label_visibility="collapsed")
                                if r2.form_submit_button("등록"):
                                    requests.post(f"{API_URL}/community/posts/{p['id']}/comments?user_id={st.session_state.user_id}", json={"content": c_txt})
                                    st.rerun()
            except: st.error("로딩 실패")

    # =========================================================================
    # [탭 6] 기관 찾기 (통합 완료)
    # =========================================================================
    with tab_map:
        st.subheader("📍 기관 찾기")
        univ_coords = {
            "연세대학교 (Sinchon)": [37.565784, 126.938572],
            "서울대학교 (Gwanak)": [37.459882, 126.951905],
            "고려대학교 (Anam)": [37.589400, 127.032300],
            "한양대학교 (Seoul)": [37.557232, 127.045322]
        }
        center = univ_coords.get(my_univ, [37.5665, 126.9780])
        
        col_opt, col_map = st.columns([1, 3])
        with col_opt:
            st.markdown(f"**기준: {my_univ}**")
            option = st.radio("기관 선택", ["🏦 은행", "🏢 관공서", "✈️ 출입국"])
            cat_map = {"🏦 은행": "BANK", "🏢 관공서": "OFFICE", "✈️ 출입국": "IMMIGRATION"}
        
        with col_map:
            try:
                res = requests.get(f"{API_URL}/agencies?category={cat_map[option]}")
                if res.status_code == 200:
                    data = res.json()
                    if data:
                        st.map(pd.DataFrame(data), latitude='lat', longitude='lon', size=200, color='#0044ff')
                        st.markdown(f"#### 🎯 {my_univ} 주변 추천")
                        nearby = [x for x in data if abs(x['lat']-center[0])<0.03 and abs(x['lon']-center[1])<0.03]
                        if nearby:
                            for place in nearby:
                                with st.container(border=True):
                                    st.markdown(f"**{place['name']}**")
                                    st.caption(f"📍 {place['address']}")
                                    st.button("길찾기", key=f"nav_{place['id']}")
                        else: st.info("근처 데이터 없음")
                    else: st.warning("데이터 없음")
            except: st.error("지도 로딩 실패")

# ==========================================
# 4. 앱 실행 분기
# ==========================================
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
    except:
        st.session_state.access_token = None
        st.rerun()
elif st.session_state.visa_type is None:
    setup_profile_page()
else:
    main_dashboard()