# frontend.py (최종 수정 완료)
import streamlit as st
import requests
from datetime import datetime, date
import pandas as pd

# 페이지 설정
st.set_page_config(page_title="Settlo", layout="wide")
API_URL = "https://settlo-647487045104.asia-northeast3.run.app/"

# 세션 상태 초기화
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "visa_type" not in st.session_state:
    st.session_state.visa_type = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# ==========================================
# 1. 로그인/회원가입 페이지
# ==========================================
def login_page():
    st.title("🌏 Settlo")
    st.subheader("외국인 유학생을 위한 AI 정착 플랫폼")
    
    col1, col2 = st.columns(2)
    
    # [왼쪽] 회원가입
    with col1:
        with st.container(border=True):
            st.markdown("### ✨ 처음 오셨나요?")
            email = st.text_input("이메일", "")
            name = st.text_input("이름", "")
            visa = st.selectbox("비자 타입", ["D-2", "D-4"])
            entry_date = st.date_input("입국일", date.today())
            
            if st.button("회원가입 및 시작하기", use_container_width=True):
                payload = {
                    "email": email, "password": "pass", "full_name": name,
                    "nationality": "Global", "visa_type": visa,
                    "university": "Univ", "entry_date": str(entry_date)
                }
                try:
                    res = requests.post(f"{API_URL}/users/signup", json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        st.session_state.user_id = data['id']
                        st.session_state.user_name = data['full_name']
                        st.session_state.visa_type = visa 
                        st.rerun()
                    else:
                        st.error(f"가입 실패: {res.text}")
                except:
                    st.error("서버 연결 실패")

    # [오른쪽] 기존 유저 로그인
    with col2:
        with st.container(border=True):
            st.markdown("### 🔑 이미 계정이 있나요?")
            input_id = st.number_input("사용자 ID 입력 (데모용)", min_value=1, step=1)
            if st.button("로그인", use_container_width=True):
                res = requests.get(f"{API_URL}/users/{input_id}/roadmap")
                if res.status_code == 200:
                    st.session_state.user_id = input_id
                    st.session_state.user_name = "User" 
                    st.session_state.visa_type = "D-2" 
                    st.success("로그인 성공!")
                    st.rerun()
                else:
                    st.error("존재하지 않는 ID입니다.")

# ==========================================
# 2. 메인 대시보드
# ==========================================
def main_dashboard():
    # 사이드바
    with st.sidebar:
        st.header(f"반가워요, {st.session_state.user_name}님! 👋")
        st.caption(f"User ID: {st.session_state.user_id}")
        
        st.divider()
        st.subheader("⚙️ 내 체류 설정")
        
        current_visa = st.session_state.get('visa_type', 'D-2')
        visa_options = ["D-2", "D-4"]
        try:
            v_index = visa_options.index(current_visa)
        except:
            v_index = 0
            
        selected_visa = st.selectbox("현재 비자 타입", visa_options, index=v_index)
        
        if selected_visa != current_visa:
            with st.spinner("로드맵을 재설정하고 있습니다..."):
                res = requests.patch(
                    f"{API_URL}/users/{st.session_state.user_id}/visa", 
                    json={"visa_type": selected_visa}
                )
                if res.status_code == 200:
                    st.session_state.visa_type = selected_visa
                    st.toast(f"비자가 {selected_visa}로 변경되었습니다!")
                    st.rerun()
        
        st.divider()
        if st.button("로그아웃"):
            st.session_state.user_id = None
            st.rerun()

    # 메인 탭
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🗺️ 로드맵", "🤖 스마트 리더", "💬 AI 상담사", "🗣️ 커뮤니티", "🏢 기관 찾기"])

    # [탭 1] 로드맵 (파트너 비교 + 단계별 Q&A Ticket System)
    with tab1:
        st.subheader(f"📋 {selected_visa} 정착 워크플로우")
        
        # 데이터 로드
        res = requests.get(f"{API_URL}/users/{st.session_state.user_id}/roadmap")
        
        if res.status_code == 200:
            roadmap_data = res.json() # 변수명 변경 (충돌 방지)
            steps = roadmap_data['steps']
            
            # 진행률 바
            total = len(steps)
            completed = len([s for s in steps if s['status'] == '완료'])
            prog = completed / total if total > 0 else 0
            st.progress(prog)
            st.caption(f"진행률: {int(prog*100)}%")
            
            st.divider()

            # 상태값 정의
            status_color = {"대기": "gray", "자료요청": "red", "검토중": "orange", "진행중": "blue", "완료": "green", "보류": "gray"}

            for step in steps:
                badge = status_color.get(step['status'], "gray")
                try:
                    d_day = (datetime.strptime(step['deadline'], '%Y-%m-%d').date() - date.today()).days
                    d_str = f"D-{d_day}" if d_day >= 0 else f"D+{abs(d_day)}"
                except: 
                    d_str = "-"
                
                # --- 카드 열기 ---
                with st.expander(f":{badge}[{step['status']}] {step['title']} ({d_str})"):
                    st.info(f"ℹ️ **Guide:** {step['description']}")
                    
                    # 1. 전문가 위임 vs 직접 하기 비교 (HOUSING, VISA, BANK)
                    if step['category'] in ['HOUSING', 'VISA', 'BANK']:
                        st.markdown("#### ⚖️ 전문가 위임 vs 직접 하기")
                        # (API 호출 최소화를 위해 try-except 처리)
                        try:
                            partner_data = requests.get(f"{API_URL}/partners/{step['category']}").json()
                            comp = partner_data['comparison']
                            
                            c1, c2 = st.columns(2)
                            with c1:
                                with st.container(border=True):
                                    st.markdown("🏃 **직접 하기**")
                                    st.caption(f"비용: {comp['self']['cost']:,}원 | 시간: {comp['self']['time']}")
                            with c2:
                                with st.container(border=True):
                                    st.markdown("🤵 **전문가 위임**")
                                    st.caption(f"비용: {comp['expert']['cost']:,}원 | 시간: {comp['expert']['time']}")

                            # 파트너 선택 및 위임 요청
                            partners = partner_data['partners']
                            sel_p = st.selectbox("파트너 선택", [p['name'] for p in partners], key=f"ps_{step['id']}")
                            if st.button("위임 요청", key=f"btn_{step['id']}"):
                                requests.patch(f"{API_URL}/roadmap-steps/{step['id']}", json={"status": "검토중"})
                                st.toast("요청 전송 완료!")
                                st.rerun()
                        except:
                            st.caption("비교 데이터 로딩 실패")
                    
                    st.markdown("---")
                    
                    # 2. 상태 변경 & 파일 업로드
                    col_st, col_file = st.columns([1, 1])
                    with col_st:
                        idx = list(status_color.keys()).index(step['status'])
                        new_st = st.selectbox("상태 변경", list(status_color.keys()), index=idx, key=f"s_{step['id']}")
                        if new_st != step['status']:
                            requests.patch(f"{API_URL}/roadmap-steps/{step['id']}", json={"status": new_st})
                            st.rerun()
                    with col_file:
                        st.file_uploader("관련 서류 첨부", key=f"fl_{step['id']}")

                    # 3. [New] 단계별 Q&A (Ticket System)
                    st.markdown("---")
                    st.subheader("💬 문의/상담 (Ticket)")
                    
                    # 댓글 목록 보여주기
                    if step['comments']:
                        for cmt in step['comments']:
                            # 내가 쓴 글 vs 전문가 글 구분 (여기선 간단히 ID로)
                            role = "나" if cmt['author_id'] == st.session_state.user_id else "전문가"
                            bg_color = "blue" if role == "나" else "green"
                            st.caption(f":{bg_color}[{role}]: {cmt['content']} ({cmt['created_at'][:10]})")
                    else:
                        st.caption("아직 문의 내역이 없습니다.")

                    # 댓글 입력창
                    with st.form(key=f"qna_form_{step['id']}"):
                        col_in, col_btn = st.columns([4, 1])
                        new_q = col_in.text_input("문의사항 입력", placeholder="예: 이 서류는 어디서 떼나요?", label_visibility="collapsed")
                        if col_btn.form_submit_button("등록"):
                            if new_q:
                                requests.post(
                                    f"{API_URL}/roadmap-steps/{step['id']}/comments?user_id={st.session_state.user_id}",
                                    json={"content": new_q}
                                )
                                st.rerun()

    # [탭 2] 문서 지갑
    with tab2:
        st.subheader("📂 디지털 문서 지갑")
        up_file = st.file_uploader("파일 업로드", type=['png', 'jpg'])
        if up_file and st.button("분석 및 저장"):
            files = {"file": (up_file.name, up_file, up_file.type)}
            up_res = requests.post(f"{API_URL}/users/{st.session_state.user_id}/documents?doc_type=PASSPORT", files=files)
            if up_res.status_code == 200:
                st.info("AI 분석 중... (만료일 추출)")
                # 데모용 ID 5 고정 (테스트 시 주의)
                an_res = requests.post(f"{API_URL}/documents/5/analyze") 
                if an_res.status_code == 200:
                    result = an_res.json()['result']
                    st.success("분석 완료!")
                    with st.expander("결과 보기", expanded=True):
                        st.json(result)
                    if result.get('expiry_date'):
                         st.error(f"📅 만료일: **{result['expiry_date']}** (캘린더 등록 권장)")
                else:
                    st.error("분석 실패")

        st.divider()
        st.caption("🔒 Security Audit Log")
        st.text("최근 활동: 문서 조회(User 1), 분석 요청(User 1) ...")

    # [탭 3] 챗봇
    with tab3:
        st.subheader("💬 AI 상담사")
        for m in st.session_state.messages:
            st.chat_message(m["role"]).write(m["content"])
            
        if q := st.chat_input("질문하세요"):
            st.session_state.messages.append({"role": "user", "content": q})
            st.chat_message("user").write(q)
            with st.spinner("답변 중..."):
                r = requests.post(f"{API_URL}/chat", json={"message": q})
                if r.status_code == 200:
                    ans = r.json()['reply']
                    st.chat_message("assistant").write(ans)
                    st.session_state.messages.append({"role": "assistant", "content": ans})

    # [탭 4] 커뮤니티 (케이스 기반 & 필터링 고도화)
    with tab4:
        st.subheader("🗣️ 케이스 공유 & 커뮤니티")
        st.caption("검증된 후기를 통해 내 상황에 맞는 정보를 찾아보세요.")

        # --- 1. 상단 필터바 (Recommendation) ---
        col_filter, col_write_btn = st.columns([3, 1])
        
        with col_filter:
            # 내 비자 타입 가져오기
            my_visa = st.session_state.get('visa_type', 'D-2')
            
            # 필터 선택 (기본값: 내 비자 위주)
            filter_opt = st.radio(
                "보고 싶은 글", 
                ["전체 보기", f"내 비자({my_visa})만 보기"], 
                horizontal=True
            )
            
            visa_param = my_visa if "내 비자" in filter_opt else "ALL"

        # --- 2. 글쓰기 영역 (Result Tagging) ---
        with st.expander("📝 새 후기 작성하기 (Case Share)"):
            with st.form("w"):
                c1, c2 = st.columns([1, 1])
                with c1:
                    # 결과 태그 선택
                    res_tag = st.selectbox("결과 유형", ["✅ 승인 (Success)", "🚫 반려 (Fail)", "💡 정보/팁 (Tip)"])
                with c2:
                    # 비자 타입 선택 (자동으로 내 비자가 잡힘)
                    v_type = st.selectbox("관련 비자", ["D-2", "D-4"], index=0 if my_visa=="D-2" else 1)

                t = st.text_input("제목", placeholder="예: D-2 비자 연장 성공 후기")
                c = st.text_area("내용", placeholder="심사 과정에서 있었던 일을 자세히 적어주세요.")
                
                if st.form_submit_button("등록"):
                    # 태그 값 변환 (한글 -> 코드)
                    tag_code = "SUCCESS" if "승인" in res_tag else "FAIL" if "반려" in res_tag else "TIP"
                    
                    requests.post(
                        f"{API_URL}/community/posts?user_id={st.session_state.user_id}", 
                        json={
                            "title":t, "content":c, 
                            "visa_type": v_type, "result_tag": tag_code
                        }
                    )
                    st.rerun()
        
        st.divider()

        # --- 3. 글 목록 조회 (필터 적용) ---
        posts_res = requests.get(f"{API_URL}/community/posts?visa_filter={visa_param}")
        
        if posts_res.status_code == 200:
            posts = posts_res.json()
            st.markdown(f"##### 🔍 총 {len(posts)}건의 사례가 있습니다.")
            
            for p in posts:
                with st.container(border=True):
                    # 태그 디자인 (Badge)
                    if p['result_tag'] == 'SUCCESS':
                        tag_badge = ":green-background[✅ 승인]"
                    elif p['result_tag'] == 'FAIL':
                        tag_badge = ":red-background[🚫 반려]"
                    else:
                        tag_badge = ":blue-background[💡 팁]"
                    
                    visa_badge = f":gray[{p['visa_type']}]"

                    # 상단 헤더
                    st.markdown(f"### {tag_badge} {p['title']}")
                    st.caption(f"{visa_badge} | 작성자 ID: {p['author_id']}")
                    
                    st.write(p['content'])
                    
                    # 본인 글 수정/삭제 (기존 유지)
                    if p['author_id'] == st.session_state.user_id:
                        c_edit, c_del = st.columns([1, 1])
                        with c_del:
                            if st.button("🗑 삭제", key=f"del_{p['id']}"):
                                requests.delete(f"{API_URL}/community/posts/{p['id']}?user_id={st.session_state.user_id}")
                                st.rerun()
                        # (수정 기능은 코드 길이상 생략, 필요시 이전 코드 복붙 가능)

                    # 댓글 영역 (기존 유지)
                    if p['comments']:
                        st.markdown("---")
                        for cmt in p['comments']:
                            st.caption(f"└ 💬 {cmt['content']}")
                    
                    with st.form(f"cmt_{p['id']}"):
                        r1, r2 = st.columns([8,2])
                        nc = r1.text_input("댓글", label_visibility="collapsed")
                        if r2.form_submit_button("등록") and nc:
                            requests.post(f"{API_URL}/community/posts/{p['id']}/comments?user_id={st.session_state.user_id}", json={"content": nc})
                            st.rerun()
        else:
            st.error("글 목록을 불러오지 못했습니다.")

    # [Tab 5] 기관 찾기 (New!)
    with tab5:
        st.subheader("📍 내 주변 필수 기관 찾기")
        st.caption("현재 위치(서울시청)를 기준으로 방문 가능한 기관을 보여줍니다.")
        
        col_opt, col_map = st.columns([1, 3])
        
        with col_opt:
            # 필터링 옵션
            option = st.radio(
                "찾고 싶은 기관", 
                ["전체 보기", "🏦 은행 (Bank)", "🏢 관공서 (Office)", "✈️ 출입국 (Immigration)"]
            )
            
            # 카테고리 매핑
            cat_map = {
                "전체 보기": "ALL", 
                "🏦 은행 (Bank)": "BANK", 
                "🏢 관공서 (Office)": "OFFICE", 
                "✈️ 출입국 (Immigration)": "IMMIGRATION"
            }
            selected_cat = cat_map[option]
            
        # API 호출
        res = requests.get(f"{API_URL}/agencies?category={selected_cat}")
        
        if res.status_code == 200:
            data = res.json()
            
            with col_map:
                if data:
                    # 데이터프레임 변환 (st.map은 df 형식을 필요로 함)
                    df = pd.DataFrame(data)
                    
                    # 지도 표시 (파란 점으로 표시됨)
                    st.map(df, latitude='lat', longitude='lon', size=20, color='#0044ff')
                else:
                    st.warning("주변에 해당 기관이 없습니다.")
            
            # 하단 리스트 뷰
            st.divider()
            st.markdown(f"### 📋 검색 결과 ({len(data)}곳)")
            
            # 3열로 카드 배치
            cols = st.columns(3)
            for idx, place in enumerate(data):
                with cols[idx % 3]:
                    with st.container(border=True):
                        # 아이콘 결정
                        icon = "🏦" if place['type'] == 'BANK' else "🏢" if place['type'] == 'OFFICE' else "✈️"
                        
                        st.markdown(f"**{icon} {place['name']}**")
                        st.caption(f"📍 {place['address']}")
                        st.text("🕒 09:00 - 16:00")
                        
                        if st.button("길찾기", key=f"nav_{place['name']}"):
                            st.toast(f"🚗 '{place['name']}'(으)로 안내를 시작합니다!")

# ==========================================
# 3. 앱 실행 분기
# ==========================================
if st.session_state.user_id is None:
    login_page()
else:
    main_dashboard()