import streamlit as st
import asyncio
from datetime import datetime
import pandas as pd
from query_action import DatabaseSearch, ResponseGeneration, ResponseReview, NewsChatbot
import os
import streamlit.components.v1 as components

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
    
    /* 인증 폼 스타일링 */
    .auth-form {
        background-color: white;
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 0 10px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    
    /* 버튼 스타일링 */
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 2.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


class AuthComponent:
    def __init__(self):
        self.init_firebase()
        self.init_session_state()

    def init_session_state(self):
        if "user" not in st.session_state:
            st.session_state.user = None
        if "show_login" not in st.session_state:
            st.session_state.show_login = False
        if "show_signup" not in st.session_state:
            st.session_state.show_signup = False

    def init_firebase(self):
        """Firebase 초기화 (HTML/JS 삽입)"""
        components.html(
            """
            <script src="https://www.gstatic.com/firebasejs/9.6.10/firebase-app-compat.js"></script>
            <script src="https://www.gstatic.com/firebasejs/9.6.10/firebase-auth-compat.js"></script>
            
            <script>
            const firebaseConfig = {
                apiKey: "AlZaSyCvqGGFFHWxTeKwHJV46F0yehf8rlaugYl",
                authDomain: "ainewschatbot.firebaseapp.com",
                projectId: "ainewschatbot",
                storageBucket: "ainewschatbot.appspot.com",
                messagingSenderId: "513924985625",
                appId: "project-513924985625"
            };

            firebase.initializeApp(firebaseConfig);
            
        // 인증 상태 변경 감지 수정
        firebase.auth().onAuthStateChanged((user) => {
            if (user) {
                const userInfo = {
                    uid: user.uid,
                    email: user.email,
                    displayName: user.displayName
                };
                // localStorage를 통해 Streamlit과 상태 공유
                localStorage.setItem('auth_user', JSON.stringify(userInfo));
                // 페이지 새로고침
                window.location.reload();
            } else {
                localStorage.removeItem('auth_user');
                window.location.reload();
            }
        });

        // Firebase 인증 함수들 수정
        function signInWithEmail(email, password) {
            firebase.auth().signInWithEmailAndPassword(email, password)
                .then((result) => {
                    console.log('로그인 성공');
                })
                .catch((error) => {
                    alert('로그인 실패: ' + error.message);
                });
        }

        function signUpWithEmail(email, password) {
            firebase.auth().createUserWithEmailAndPassword(email, password)
                .then((result) => {
                    console.log('회원가입 성공');
                })
                .catch((error) => {
                    alert('회원가입 실패: ' + error.message);
                });
        }

        // 페이지 로드 시 로그인 상태 확인
        window.addEventListener('load', () => {
            const user = JSON.parse(localStorage.getItem('auth_user'));
            if (user) {
                window.parent.postMessage({
                    type: 'AUTH_STATE_CHANGED',
                    user: user
                }, '*');
            }
        });
        </script>
        """,
            height=0,
        )

    # 로컬 스토리지에서 사용자 정보 확인
    components.html(
        """
        <script>
        const user = JSON.parse(localStorage.getItem('auth_user'));
        if (user) {
            window.parent.postMessage({
                type: 'AUTH_STATE_CHANGED',
                user: user
            }, '*');
        }
        </script>
        """,
        height=0,
    )

    def render_auth_buttons(self):
        """상단 로그인/회원가입/로그아웃 버튼 영역"""
        container = st.container()
        with container:
            cols = st.columns([6, 1, 1])

            if st.session_state.user:
                with cols[2]:
                    if st.button("로그아웃"):
                        components.html(
                            """
                            <script>
                            signOut();
                            </script>
                            """,
                            height=0,
                        )
                        st.session_state.user = None
                        st.experimental_rerun()
            else:
                with cols[1]:
                    if st.button("로그인"):
                        st.session_state.show_login = True
                        st.session_state.show_signup = False
                with cols[2]:
                    if st.button("회원가입"):
                        st.session_state.show_signup = True
                        st.session_state.show_login = False

    def render_login_form(self):
        """로그인 폼"""
        if st.session_state.show_login:
            with st.container():
                with st.form("login_form", clear_on_submit=True):
                    col1, col2 = st.columns([10, 2])
                    with col2:
                        if st.form_submit_button("✕"):
                            st.session_state.show_login = False
                            st.experimental_rerun()

                    st.markdown("### 로그인")

                    # Google 로그인 버튼
                    if st.form_submit_button(
                        "🌐 Google로 로그인", use_container_width=True
                    ):
                        components.html(
                            """
                            <script>
                            signInWithGoogle();
                            </script>
                            """,
                            height=0,
                        )

                    st.markdown("---")

                    email = st.text_input("이메일")
                    password = st.text_input("비밀번호", type="password")

                    if st.form_submit_button("로그인", use_container_width=True):
                        if email and password:
                            components.html(
                                f"""
                                <script>
                                signInWithEmail('{email}', '{password}');
                                </script>
                                """,
                                height=0,
                            )

    def render_signup_form(self):
        """회원가입 폼"""
        if st.session_state.show_signup:
            with st.container():
                with st.form("signup_form", clear_on_submit=True):
                    col1, col2 = st.columns([10, 2])
                    with col2:
                        if st.form_submit_button("✕"):
                            st.session_state.show_signup = False
                            st.experimental_rerun()

                    st.markdown("### 회원가입")

                    email = st.text_input("이메일")
                    password = st.text_input("비밀번호", type="password")
                    confirm_password = st.text_input("비밀번호 확인", type="password")

                    if st.form_submit_button("가입하기", use_container_width=True):
                        if not email or not password:
                            st.error("모든 필드를 입력해주세요.")
                        elif password != confirm_password:
                            st.error("비밀번호가 일치하지 않습니다.")
                        else:
                            components.html(
                                f"""
                                <script>
                                signUpWithEmail('{email}', '{password}');
                                </script>
                                """,
                                height=0,
                            )


class StreamlitChatbot:
    def __init__(self):
        # 인증 컴포넌트 초기화
        self.auth = AuthComponent()
        self.init_session_state()

    def init_session_state(self):
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

    async def process_user_input(self, user_input):
        """사용자 입력 처리 (비동기)"""
        if not user_input:
            return

        # 사용자 메시지 표시
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.status("AI가 답변을 생성하고 있습니다...") as status:
            try:
                main_article, related_articles, score, response = (
                    await st.session_state.chatbot.process_query(user_input)
                )

                # "개선된 답변", "개선 사항", "개선점" 필터링
                lines = response.splitlines()
                filtered_lines = []
                skip_remaining = False

                for line in lines:
                    # "개선된 답변" 이 들어간 줄 → 건너뛰기
                    if "개선된 답변" in line:
                        continue
                    # "개선 사항" 또는 "개선점" 발견 시 → 그 줄부터 모두 건너뛰기
                    if ("개선 사항" in line) or ("개선점" in line):
                        skip_remaining = True
                    # skip_remaining이 False면 라인 추가
                    if not skip_remaining:
                        filtered_lines.append(line)

                cleaned_response = "\n".join(filtered_lines)

                combined_articles = (
                    [main_article] + related_articles if main_article else []
                )

                # 어시스턴트 메시지
                with st.chat_message("assistant"):
                    st.markdown(cleaned_response)
                    if combined_articles:
                        st.markdown("### 📚 관련 기사")
                        for i in range(0, min(len(combined_articles), 4), 2):
                            col1, col2 = st.columns(2)
                            with col1:
                                if i < len(combined_articles):
                                    article = combined_articles[i]
                                    st.markdown(
                                        f"""
                                        #### {i+1}. {article.get('title', '제목 없음')}
                                        - 📅 발행일: {article.get('published_date', '날짜 정보 없음')}
                                        - 🔗 [기사 링크]({article.get('url', '#')})
                                        - 📊 카테고리: {', '.join(article.get('categories', ['미분류']))}
                                        """
                                    )
                            with col2:
                                if i + 1 < len(combined_articles):
                                    article = combined_articles[i + 1]
                                    st.markdown(
                                        f"""
                                        #### {i+2}. {article.get('title', '제목 없음')}
                                        - 📅 발행일: {article.get('published_date', '날짜 정보 없음')}
                                        - 🔗 [기사 링크]({article.get('url', '#')})
                                        - 📊 카테고리: {', '.join(article.get('categories', ['미분류']))}
                                        """
                                    )

                # 히스토리 업데이트
                if main_article:
                    st.session_state.article_history.append(main_article)
                    st.session_state.search_history.append(
                        {
                            "question": user_input,
                            "answer": cleaned_response,
                            "articles": combined_articles,
                        }
                    )

                status.update(label="완료!", state="complete")

            except Exception as e:
                st.error(f"오류가 발생했습니다: {str(e)}")
                status.update(label="오류 발생", state="error")

    def show_analytics(self):
        """검색 통계 표시"""
        if st.session_state.article_history:
            st.header("📊 검색 분석")

            # 카테고리
            categories = []
            for article in st.session_state.article_history:
                categories.extend(article.get("categories", ["미분류"]))

            df_categories = pd.DataFrame(categories, columns=["카테고리"])
            category_counts = df_categories["카테고리"].value_counts()

            # 날짜
            dates = [
                datetime.fromisoformat(
                    art.get("published_date", datetime.now().isoformat())
                )
                for art in st.session_state.article_history
            ]
            df_dates = pd.DataFrame(dates, columns=["발행일"])
            date_counts = df_dates["발행일"].dt.date.value_counts()

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("📈 카테고리별 기사 분포")
                if not category_counts.empty:
                    st.bar_chart(category_counts)
                    st.markdown("**카테고리별 비율:**")
                    for cat, count in category_counts.items():
                        percentage = (count / len(categories)) * 100
                        st.write(f"- {cat}: {percentage:.1f}% ({count}건)")
                else:
                    st.info("아직 카테고리 데이터가 없습니다.")

            with col2:
                st.subheader("📅 일자별 기사 분포")
                if not date_counts.empty:
                    st.line_chart(date_counts)
                    st.markdown("**날짜별 기사 수:**")
                    for date, count in date_counts.sort_index(ascending=False).items():
                        st.write(f"- {date.strftime('%Y-%m-%d')}: {count}건")
                else:
                    st.info("아직 날짜 데이터가 없습니다.")

            st.subheader("🔍 검색 통계")
            col3, col4, col5 = st.columns(3)
            with col3:
                st.metric(
                    label="총 검색 수", value=len(st.session_state.search_history)
                )
            with col4:
                st.metric(
                    label="검색된 총 기사 수",
                    value=len(st.session_state.article_history),
                )
            with col5:
                if st.session_state.article_history:
                    latest_article = max(
                        st.session_state.article_history,
                        key=lambda x: x.get("published_date", ""),
                    )
                    st.metric(
                        label="최신 기사 날짜",
                        value=datetime.fromisoformat(
                            latest_article.get(
                                "published_date", datetime.now().isoformat()
                            )
                        ).strftime("%Y-%m-%d"),
                    )

            # 최근 검색어
            if st.session_state.search_history:
                st.subheader("🕒 최근 검색어")
                recent_searches = st.session_state.search_history[-5:]
                for item in reversed(recent_searches):
                    st.text(f"• {item['question']}")
        else:
            st.info("아직 검색 결과가 없습니다. 질문을 입력해주세요!")


def render_sidebar():
    """사이드바"""
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

    # 인증 컴포넌트 렌더링
    app.auth.render_auth_buttons()

    # 로그인/회원가입 폼 렌더링 (로그인되지 않은 경우에만)
    if not st.session_state.user:
        app.auth.render_login_form()
        app.auth.render_signup_form()
        st.info("서비스를 이용하려면 로그인해주세요.")
        return

    # 로그인된 경우 메인 컨텐츠 표시
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

    render_sidebar()

    if st.session_state.selected_chat:
        with st.chat_message("user"):
            st.markdown(st.session_state.selected_chat["question"])
        with st.chat_message("assistant"):
            st.markdown(st.session_state.selected_chat["response"])
            if st.session_state.selected_chat["articles"]:
                st.markdown("### 📚 관련 기사")
                for i, article in enumerate(st.session_state.selected_chat["articles"]):
                    st.markdown(
                        f"""
                    #### {i+1}. {article.get('title', '제목 없음')}
                    - 📅 발행일: {article.get('published_date', '날짜 정보 없음')}
                    - 🔗 [기사 링크]({article.get('url', '#')})
                    - 📊 카테고리: {', '.join(article.get('categories', ['미분류']))}
                    """
                    )

    user_input = st.chat_input("메시지를 입력하세요...")
    if user_input:
        asyncio.run(app.process_user_input(user_input))
    else:
        st.info("서비스를 이용하려면 로그인해주세요.")


if __name__ == "__main__":
    main()
