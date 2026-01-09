import streamlit as st
import requests
from datetime import datetime, date
import pandas as pd
import time

# 페이지 설정
st.set_page_config(page_title="Settlo", layout="wide", page_icon="🌏")

# API 주소
API_URL = "http://localhost:8000"

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
    # 사이드바
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

    # 메인 탭
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🗺️ 로드맵", "🤖 스마트 리더", "💬 AI 상담사", "🗣️ 커뮤니티", "🏢 기관 찾기"])

    # [탭 1] 로드맵 (핵심 업그레이드: 문서 제출 기능 연동)
    with tab1:
        if st.session_state.user_id:
            try:
                res = requests.get(f"{API_URL}/users/{st.session_state.user_id}/roadmap")
                if res.status_code == 200:
                    roadmap_data = res.json()
                    steps = roadmap_data.get('steps', [])
                    if not steps: st.info("로드맵 생성 중...")
                    else:
                        total = len(steps)
                        completed_steps = [s for s in steps if s['status'] == '완료']
                        prog = len(completed_steps) / total if total > 0 else 0
                        current_step = next((s for s in steps if s['status'] != '완료'), None)
                        
                        with st.container(border=True):
                            c1, c2 = st.columns([1, 2])
                            with c1:
                                st.metric("정착 진행률", f"{int(prog*100)}%")
                                st.progress(prog)
                            with c2:
                                univ_name = my_univ.split(' ')[0]
                                st.markdown(f"#### 🏫 **{univ_name}** 학생을 위한 가이드")
                                st.caption(f"거주 관할: {my_region} | 비자: {st.session_state.visa_type}")
                                
                                if current_step:
                                    if current_step.get('deadline'):
                                        d_day = (datetime.strptime(current_step['deadline'], '%Y-%m-%d').date() - date.today()).days
                                        d_str = f"D-{d_day}" if d_day >= 0 else f"D+{abs(d_day)}"
                                        st.caption(f"🔥 **{current_step['title']}** 마감: {current_step['deadline']} ({d_str})")

                        st.divider()
                        st.subheader("단계별 워크플로우")

                        status_color = {"대기": "gray", "자료요청": "red", "검토중": "orange", "진행중": "blue", "완료": "green"}
                        meta_info = {
                            "ENTRY": {"time": "30분", "cost": "무료"},
                            "HOUSING": {"time": "1~2주", "cost": "보증금별 상이"},
                            "VISA": {"time": "3주", "cost": "6~13만원"},
                            "BANK": {"time": "1시간", "cost": "없음"}
                        }

                        for step in steps:
                            badge = status_color.get(step['status'], "gray")
                            meta = meta_info.get(step['category'], {"time": "-", "cost": "-"})
                            is_expanded = (step['id'] == current_step['id']) if current_step else False
                            
                            with st.expander(f":{badge}[{step['status']}] {step['title']}", expanded=is_expanded):
                                desc = step['description']
                                if step['category'] == "VISA": desc += f" (관할: {my_region})"
                                elif step['category'] == "BANK": desc += f" ({univ_name} 학생증 우대)"
                                
                                m1, m2, m3 = st.columns([2, 1, 1])
                                m1.info(f"💡 {desc}")
                                m2.caption(f"⏱️ {meta['time']}")
                                m3.caption(f"💰 {meta['cost']}")
                                
                                st.markdown("---")
                                
                                # A. 체크리스트
                                st.markdown("#### ✅ 체크리스트")
                                if step.get('checklist'):
                                    all_chk = True
                                    for item in step['checklist']:
                                        chk = st.checkbox(item['item_content'], value=item['is_checked'], key=f"c_{item['id']}")
                                        if not chk: all_chk = False
                                        if chk != item['is_checked']:
                                            requests.patch(f"{API_URL}/checklist-items/{item['id']}", json={"is_checked": chk})
                                            st.rerun()
                                else:
                                    st.caption("체크리스트 없음")
                                    all_chk = True 

                                st.markdown("---")

                                # B. [NEW] 문서 제출 및 상태 확인 (기획서 구현 핵심)
                                st.markdown("#### 📂 필수 서류 제출")
                                
                                # (1) 제출된 문서 목록
                                if step.get('documents'):
                                    for doc in step['documents']:
                                        icon = "✅" if doc['verification_status'] == "PASSED" else "🟡"
                                        st.info(f"{icon} **제출됨:** {doc['doc_type']} (상태: {doc['verification_status']})")
                                else:
                                    st.caption("아직 제출된 서류가 없습니다.")

                                # (2) 새로 업로드하기
                                if step['status'] != "완료":
                                    with st.form(f"up_{step['id']}"):
                                        dtype = "CONTRACT" if step['category'] == "HOUSING" else "PASSPORT"
                                        upl = st.file_uploader("서류 첨부 (자동 분석)", type=['jpg','png','pdf'])
                                        if st.form_submit_button("제출하기") and upl:
                                            files = {"file": (upl.name, upl, upl.type)}
                                            # step_id를 파라미터로 전달하여 해당 단계에 문서 귀속
                                            u_res = requests.post(
                                                f"{API_URL}/users/{st.session_state.user_id}/documents?doc_type={dtype}&step_id={step['id']}", 
                                                files=files
                                            )
                                            if u_res.status_code == 200:
                                                st.success("제출 완료! 상태가 '검토중'으로 변경됩니다.")
                                                time.sleep(1)
                                                st.rerun()
                                            else:
                                                st.error("제출 실패")

                                st.markdown("---")
                                
                                # C. 액션 버튼
                                col_act, col_exp = st.columns([1, 1])
                                with col_act:
                                    if step['status'] != "완료":
                                        if all_chk:
                                            if st.button("🎉 완료하기", key=f"fin_{step['id']}", type="primary"):
                                                requests.patch(f"{API_URL}/roadmap-steps/{step['id']}", json={"status": "완료"})
                                                st.balloons()
                                                time.sleep(1)
                                                st.rerun()
                                        else: st.button("완료 (체크리스트 미달)", key=f"dis_{step['id']}", disabled=True)
                                    else:
                                        if st.button("다시 대기로", key=f"rev_{step['id']}"):
                                            requests.patch(f"{API_URL}/roadmap-steps/{step['id']}", json={"status": "대기"})
                                            st.rerun()
                                
                                # D. 전문가 비교
                                if step['category'] in ['HOUSING', 'VISA'] and step['status'] != "완료":
                                    with st.expander("⚖️ 직접 하기 vs 전문가 위임"):
                                        try:
                                            comp = requests.get(f"{API_URL}/partners/{step['category']}").json()['comparison']
                                            c1, c2 = st.columns(2)
                                            with c1:
                                                st.info(f"🏃 {comp['self']['title']}")
                                                st.caption(f"비용: {comp['self']['cost']} | 시간: {comp['self']['time']}")
                                            with c2:
                                                st.success(f"🤵 {comp['expert']['title']}")
                                                st.caption(f"비용: {comp['expert']['cost']} | 시간: {comp['expert']['time']}")
                                            
                                            st.markdown("---")
                                            st.caption("🏅 추천 파트너")
                                            for pt in comp['expert']['partners']:
                                                with st.container(border=True):
                                                    col_p1, col_p2 = st.columns([3, 1])
                                                    col_p1.markdown(f"**{pt['name']}** ⭐ {pt['rating']}")
                                                    col_p1.caption(f"{pt['badge']} | {pt['sla']}")
                                                    col_p2.button("예약", key=f"book_{step['id']}_{pt['name']}")
                                        except: st.caption("정보 로딩 실패")

            except Exception as e: st.error(f"오류: {e}")

    # [탭 2] 문서 지갑 (스마트 리더: 대안 제시 기능 추가)
    with tab2:
        st.subheader("📂 문서 지갑")
        doc_option = st.radio("문서 종류", ["🛂 여권/등록증", "📜 임대차/근로 계약서"], horizontal=True)
        doc_type_code = "PASSPORT" if "여권" in doc_option else "CONTRACT"
        
        up_file = st.file_uploader("파일 업로드", type=['png', 'jpg', 'pdf'])
        
        if up_file and st.button("업로드 및 AI 정밀 분석"):
            files = {"file": (up_file.name, up_file, up_file.type)}
            with st.spinner("AI가 문서를 꼼꼼히 살피고 있습니다..."):
                try:
                    res = requests.post(f"{API_URL}/users/{st.session_state.user_id}/documents?doc_type={doc_type_code}", files=files)
                    if res.status_code == 200:
                        new_doc_id = res.json().get("id")
                        if not new_doc_id:
                            st.error("문서 ID 오류")
                        else:
                            an_res = requests.post(f"{API_URL}/documents/{new_doc_id}/analyze?user_id={st.session_state.user_id}")
                            if an_res.status_code == 200:
                                result = an_res.json().get('result', {})
                                st.divider()
                                
                                if doc_type_code == "CONTRACT":
                                    raw_score = result.get('risk_score', 0)
                                    try: score = int(raw_score)
                                    except: score = 0
                                    color = "red" if score >= 70 else "orange" if score >= 30 else "green"
                                    
                                    c1, c2 = st.columns([1, 3])
                                    with c1:
                                        st.markdown(f"### 위험도: :{color}[{score}점]")
                                        if score >= 70: st.error("🚨 전문가 검토 강력 추천!")
                                        elif score >= 30: st.warning("⚠️ 주의 조항 있음")
                                        else: st.success("✅ 비교적 안전")
                                    with c2: st.info(f"**요약:** {result.get('summary', '내용 없음')}")

                                    if result.get('risk_factors'):
                                        st.markdown("#### 🚫 주의해야 할 조항 (Toxic Clauses)")
                                        for risk in result['risk_factors']:
                                            with st.expander(f"⚠️ {risk.get('reason')}", expanded=True):
                                                st.markdown(f"**원문:** `{risk.get('clause')}`")
                                                st.caption(f"심각도: {risk.get('severity')}")
                                                # [NEW] 대안 제시 표시
                                                if risk.get('suggestion'):
                                                    st.info(f"💡 **수정 제안** {risk.get('suggestion')}")
                                    else:
                                        st.caption("발견된 특이 위험 조항이 없습니다.")
                                else:
                                    st.success("분석 완료!")
                                    st.json(result)
                                    if result.get('expiry_date'):
                                        st.error(f"📅 만료일: **{result['expiry_date']}**")
                            else: st.warning("분석 실패")
                    else: st.error("업로드 실패")
                except Exception as e: st.error(f"오류: {e}")

        st.divider()
        with st.expander("🛡️ 문서 접근 및 보안 로그 (Trust Log)"):
            try:
                logs_res = requests.get(f"{API_URL}/users/{st.session_state.user_id}/audit-logs")
                if logs_res.status_code == 200:
                    logs = logs_res.json()
                    if logs:
                        df_logs = pd.DataFrame(logs)
                        df_logs = df_logs[['timestamp', 'action', 'target_id']]
                        df_logs.columns = ["시간", "활동 내용", "대상 ID"]
                        st.dataframe(df_logs, width="stretch")
                    else: st.caption("아직 기록된 로그가 없습니다.")
            except: st.caption("로그를 불러올 수 없습니다.")

    # [탭 3] AI 상담사 (기존 유지)
    with tab3:
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
                    c1.button("예약 (김정수)", key=f"v1_{m['content'][:5]}")
                    c2.button("예약 (Global)", key=f"v2_{m['content'][:5]}")

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

    # [탭 4] 커뮤니티 (기존 유지)
    with tab4:
        st.subheader("🗣️ 커뮤니티")
        my_visa = st.session_state.get('visa_type', 'D-2')
        opt = st.radio("필터", ["전체", f"내 비자({my_visa})"], horizontal=True)
        v_param = my_visa if "내 비자" in opt else "ALL"

        with st.expander("📝 새 글 작성하기"):
            with st.form("new_post"):
                c1, c2 = st.columns([1, 1])
                res_tag = c1.selectbox("유형", ["✅ 승인 (Success)", "🚫 반려 (Fail)", "💡 정보 (Tip)"])
                v_type = c2.selectbox("비자", ["D-2", "D-4"])
                title = st.text_input("제목")
                content = st.text_area("내용")
                if st.form_submit_button("등록"):
                    requests.post(f"{API_URL}/community/posts?user_id={st.session_state.user_id}", json={"title": title, "content": content, "visa_type": v_type, "result_tag": res_tag})
                    st.rerun()
        st.divider()
        try:
            posts = requests.get(f"{API_URL}/community/posts?visa_filter={v_param}").json()
            for p in posts:
                with st.container(border=True):
                    tag_color = "green" if p['result_tag'] == "SUCCESS" else "red" if p['result_tag'] == "FAIL" else "blue"
                    st.markdown(f":{tag_color}-background[{p['result_tag']}] **{p['title']}**")
                    st.caption(f"{p['visa_type']} | {p['content']}")
                    if p.get('comments'):
                        st.markdown("---")
                        for comment_item in p['comments']: st.caption(f"└ {comment_item['content']}")
                    with st.form(f"cmt_{p['id']}"):
                        r1, r2 = st.columns([5, 1])
                        comment_text = r1.text_input("댓글", label_visibility="collapsed")
                        if r2.form_submit_button("등록") and comment_text:
                            requests.post(f"{API_URL}/community/posts/{p['id']}/comments?user_id={st.session_state.user_id}", json={"content": comment_text})
                            st.rerun()
        except: st.caption("글 로딩 실패")

    # [탭 5] 기관 찾기 (기존 유지)
    with tab5:
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