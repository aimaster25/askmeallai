import streamlit as st
import asyncio
from datetime import datetime, timedelta
import pandas as pd
from query_action import DatabaseSearch, ResponseGeneration, ResponseReview, NewsChatbot
import os
import streamlit.components.v1 as components
import pyrebase


# 페이지 설정
st.set_page_config(
    page_title="AI Chat",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 커스텀 CSS
st.markdown(
    """
    <style>
    /* 전체 배경색 */
    .stApp {
        background-color: white;
    }
    
    /* 사이드바 스타일링 */
    .css-1d391kg {
        padding-top: 2rem;
    }
    
    /* 채팅 메시지 스타일링 */
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        background-color: #f7f7f8;
    }
    
    /* 채팅 기록 스타일링 */
    .chat-history-item {
        padding: 0.5rem;
        cursor: pointer;
        border-radius: 0.3rem;
    }
    .chat-history-item:hover {
        background-color: #f0f0f0;
    }
    
    /* 모델 선택 드롭다운 스타일링 */
    .model-selector {
        margin-top: 1rem;
        width: 100%;
    }
    
    /* 헤더 아이콘 스타일링 */
    .header-icon {
        font-size: 1.2rem;
        margin-right: 0.5rem;
        color: #666;
    }
    
    /* 검색창 스타일링 */
    .search-box {
        padding: 0.5rem;
        border-radius: 0.3rem;
        border: 1px solid #ddd;
        margin-bottom: 1rem;
    }
    
    /* 로그인/회원가입 팝업 스타일링 */
    .auth-popup {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 0 10px rgba(0,0,0,0.2);
        margin: auto;
        max-width: 400px;
    }
    </style>
""",
    unsafe_allow_html=True,
)


class FirebaseManager:
    def __init__(self):
        self.firebase_config = {
            "apiKey": "AlZaSyCvqGGFFHWxTeKwHJV46F0yehf8rlaugYl",
            "authDomain": "ainewschatbot.firebaseapp.com",
            "projectId": "ainewschatbot",
            "storageBucket": "ainewschatbot.appspot.com",
            "messagingSenderId": "513924985625",
            "appId": "project-513924985625",
            "databaseURL": "",
        }

        # Firebase 초기화
        self.firebase = pyrebase.initialize_app(self.firebase_config)
        self.auth = self.firebase.auth()

    def sign_in_with_email(self, email, password):
        try:
            user = self.auth.sign_in_with_email_and_password(email, password)
            return True, user
        except Exception as e:
            return False, str(e)

    def sign_up_with_email(self, email, password):
        try:
            user = self.auth.create_user_with_email_and_password(email, password)
            return True, user
        except Exception as e:
            return False, str(e)

    def sign_in_with_google(self):
        try:
            auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={self.firebase_config['clientId']}&response_type=token&scope=email%20profile&redirect_uri={self.firebase_config['authDomain']}"
            return auth_url
        except Exception as e:
            return None


class StreamlitChatbot:
    def __init__(self):
        # Firebase 관리자 초기화
        self.firebase_manager = FirebaseManager()

        # 세션 상태 초기화
        self.init_session_state()

    def init_session_state(self):
        """모든 세션 상태 초기화를 한 곳에서 처리"""
        # 인증 관련 상태
        if "user" not in st.session_state:
            st.session_state.user = None
        if "show_login" not in st.session_state:
            st.session_state.show_login = False
        if "show_signup" not in st.session_state:
            st.session_state.show_signup = False

        # 채팅 관련 상태
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = {
                "today": [],
                "yesterday": [],
                "previous_7_days": [],
            }
        if "current_model" not in st.session_state:
            st.session_state.current_model = "Gemini"
        if "selected_chat" not in st.session_state:
            st.session_state.selected_chat = None
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "search_query" not in st.session_state:
            st.session_state.search_query = ""
        if "search_history" not in st.session_state:
            st.session_state.search_history = []
        if "article_history" not in st.session_state:
            st.session_state.article_history = []
        if "chatbot" not in st.session_state:
            st.session_state.chatbot = NewsChatbot()

    # [이전의 display_chat_message, process_user_input, show_analytics 메서드들은 그대로 유지]

    def render_auth_buttons(self):
        """우측 상단 인증 버튼 렌더링"""
        with st.container():
            cols = st.columns([8, 1, 1])

            if st.session_state.user:
                with cols[2]:
                    if st.button("로그아웃", key="logout_btn"):
                        st.session_state.user = None
                        st.experimental_rerun()
            else:
                with cols[1]:
                    if st.button("로그인", key="login_btn"):
                        st.session_state.show_login = True
                        st.session_state.show_signup = False
                with cols[2]:
                    if st.button("회원가입", key="signup_btn"):
                        st.session_state.show_signup = True
                        st.session_state.show_login = False

    def render_login_popup(self):
        """로그인 팝업 렌더링"""
        if st.session_state.show_login:
            with st.container():
                col1, col2 = st.columns([10, 2])
                with col2:
                    if st.button("✕", key="close_login"):
                        st.session_state.show_login = False
                        st.experimental_rerun()

                st.markdown("### 로그인")

                # Google 로그인 버튼
                if st.button(
                    "🌐 Google 계정으로 계속하기",
                    key="google_login",
                    use_container_width=True,
                ):
                    auth_url = self.firebase_manager.sign_in_with_google()
                    if auth_url:
                        st.markdown(
                            f'<a href="{auth_url}" target="_self">Google 계정으로 로그인</a>',
                            unsafe_allow_html=True,
                        )

                st.markdown("---")

                with st.form("login_form", clear_on_submit=True):
                    email = st.text_input("이메일")
                    password = st.text_input("비밀번호", type="password")
                    submit = st.form_submit_button("로그인", use_container_width=True)

                    if submit and email and password:
                        success, user = self.firebase_manager.sign_in_with_email(
                            email, password
                        )
                        if success:
                            st.session_state.user = user
                            st.session_state.show_login = False
                            st.success("로그인 성공!")
                            st.experimental_rerun()
                        else:
                            st.error(
                                "로그인 실패: 이메일 또는 비밀번호를 확인해주세요."
                            )

    def render_signup_popup(self):
        """회원가입 팝업 렌더링"""
        if st.session_state.show_signup:
            with st.container():
                col1, col2 = st.columns([10, 2])
                with col2:
                    if st.button("✕", key="close_signup"):
                        st.session_state.show_signup = False
                        st.experimental_rerun()

                st.markdown("### 회원가입")

                with st.form("signup_form", clear_on_submit=True):
                    email = st.text_input("이메일")
                    password = st.text_input("비밀번호", type="password")
                    confirm_password = st.text_input("비밀번호 확인", type="password")
                    submit = st.form_submit_button("가입하기", use_container_width=True)

                    if submit:
                        if not email or not password:
                            st.error("모든 필드를 입력해주세요.")
                        elif password != confirm_password:
                            st.error("비밀번호가 일치하지 않습니다.")
                        else:
                            success, user = self.firebase_manager.sign_up_with_email(
                                email, password
                            )
                            if success:
                                st.session_state.user = user
                                st.session_state.show_signup = False
                                st.success("회원가입 성공!")
                                st.experimental_rerun()
                            else:
                                st.error(
                                    "회원가입 실패: 이미 가입된 이메일이거나 올바르지 않은 형식입니다."
                                )


def render_sidebar():
    """사이드바 렌더링"""
    with st.sidebar:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("### 검색 히스토리")
        with col2:
            if st.button("대화 삭제"):
                st.session_state.messages = []
                st.session_state.search_history = []
                st.session_state.article_history = []
                st.session_state.selected_chat = None
                st.experimental_rerun()

        for i, item in enumerate(st.session_state.search_history):
            q = item["question"]
            if st.button(q if q else "무제", key=f"search_history_{i}"):
                st.session_state.selected_chat = {
                    "question": item["question"],
                    "response": item["answer"],
                    "articles": item["articles"],
                }


def main():
    app = StreamlitChatbot()

    # 인증 버튼 렌더링
    app.render_auth_buttons()
    app.render_login_popup()
    app.render_signup_popup()

    st.markdown(
        """
    ### 👋 안녕하세요! AI 뉴스 챗봇입니다.
    뉴스 기사에 대해 궁금한 점을 자유롭게 물어보세요. 관련 기사를 찾아 답변해드립니다.
    
    **예시 질문:**
    - "최근 AI 기술 동향이 궁금해요"
    - "스타트업 투자 현황에 대해 알려주세요"
    - "새로운 AI 서비스에는 어떤 것들이 있나요?"
    """
    )

    # 사이드바 출력
    render_sidebar()

    # 채팅 메시지 표시
    if st.session_state.selected_chat:
        app.display_chat_message("user", st.session_state.selected_chat["question"])
        app.display_chat_message(
            "assistant",
            st.session_state.selected_chat["response"],
            st.session_state.selected_chat["articles"],
        )

    # 사용자 입력 처리
    user_input = st.chat_input("메시지를 입력하세요...")
    if user_input:
        asyncio.run(app.process_user_input(user_input))


if __name__ == "__main__":
    main()
