import streamlit as st
import json
import re
from datetime import datetime
import pandas as pd
import os

# 페이지 설정
st.set_page_config(
    page_title="AI 인권 지킴이 챗봇 🤖",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Streamlit Cloud에서 AI 모델 사용 여부 확인
@st.cache_data
def check_ai_availability():
    """AI 모델 사용 가능 여부 확인"""
    try:
        import transformers
        import torch
        return True
    except ImportError:
        return False

# AI 모델 로드 (캐시 적용)
@st.cache_resource
def load_ai_model():
    """경량 AI 모델 로드"""
    try:
        from transformers import pipeline
        # 가벼운 감정 분석 모델 사용 (한국어 지원)
        classifier = pipeline(
            "text-classification", 
            model="beomi/KcELECTRA-base-v2022",
            return_all_scores=True
        )
        return classifier
    except Exception as e:
        st.error(f"AI 모델 로드 실패: {str(e)}")
        return None

# 확장된 인권 침해 키워드 사전
HUMAN_RIGHTS_KEYWORDS = {
    "차별": [
        "차별", "따돌림", "괴롭힘", "무시", "배제", "구별", "편견", 
        "흑인", "고릴라", "피부색", "인종", "외국인", "다문화", 
        "장애인", "장애", "못생겼다", "뚱뚱하다", "키 작다", "가난하다"
    ],
    "폭력": [
        "때리기", "폭력", "체벌", "구타", "때림", "맞음", "상처", 
        "밀치기", "할퀴기", "꼬집기", "발로 차기", "던지기"
    ],
    "사생활 침해": [
        "사생활", "개인정보", "비밀", "몰래", "훔쳐봄", "엿듣기", 
        "몰래카메라", "사진 찍기", "녹음", "일기 보기", "가방 뒤지기"
    ],
    "교육권": [
        "공부", "교육", "학교", "수업", "배움", "가르침", 
        "학원 못 가기", "책 없음", "컴퓨터 없음", "인터넷 없음"
    ],
    "표현의 자유": [
        "말하기", "의견", "생각", "표현", "발표", "글쓰기", 
        "입 막기", "조용히 해", "말 못하게", "검열"
    ],
    "건강권": [
        "건강", "의료", "치료", "병원", "아픔", "다침", 
        "급식", "물", "화장실", "환기", "청결", "위생"
    ],
    "휴식권": [
        "휴식", "놀이", "쉬기", "자유시간", "여가", "놀이터", 
        "공원", "운동장", "게임", "만화", "텔레비전"
    ],
    "편의시설 접근권": [
        "세면대", "화장실", "엘리베이터", "경사로", "휠체어", 
        "계단", "문턱", "높이", "손이 닿지 않는", "이용할 수 없는"
    ],
    "주거환경권": [
        "놀이터", "공원", "아파트", "집", "소음", "먼지", 
        "위험한 길", "어두운 곳", "CCTV", "안전"
    ]
}

# 관련 법률 정보
RELATED_LAWS = {
    "차별": {
        "법률": "헌법 제11조, 장애인차별금지법, 인종차별철폐협약",
        "내용": "모든 사람은 평등하게 대우받을 권리가 있어요.",
        "설명": "피부색, 외모, 장애, 가족의 직업 등으로 친구를 차별하면 안 돼요. 모든 사람은 소중하고 똑같이 존중받아야 해요. 흑인을 동물에 비유하는 것도 심각한 차별이에요."
    },
    "편의시설 접근권": {
        "법률": "장애인차별금지법, 교육환경보호법, 어린이놀이시설안전관리법",
        "내용": "모든 사람이 편리하게 이용할 수 있는 시설을 이용할 권리가 있어요.",
        "설명": "어린이 키에 맞는 세면대, 장애인이 이용할 수 있는 화장실 등이 필요해요. 모든 사람이 불편 없이 이용할 수 있어야 해요."
    },
    "주거환경권": {
        "법률": "주택법, 어린이놀이시설안전관리법, 도시공원법",
        "내용": "안전하고 건강한 환경에서 살 권리가 있어요.",
        "설명": "아파트에는 어린이가 놀 수 있는 놀이터나 공간이 있어야 해요. 안전하고 깨끗한 환경에서 살 권리가 있어요."
    }
}

# 세션 상태 초기화
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = []

def analyze_human_rights_violation(text):
    """텍스트에서 인권 침해 요소 분석"""
    violations = []
    text_lower = text.lower()
    
    # 특별한 패턴 감지
    special_patterns = {
        "인종차별": ["흑인.*고릴라", "피부.*색깔.*동물", "외국인.*못생겼다"],
        "편의시설": ["어린이.*세면대.*없", "키.*맞지.*않", "높아서.*이용.*못", "세면대.*높"],
        "환경권": ["놀이터.*없", "공원.*없", "놀.*곳.*없"]
    }
    
    # 특별 패턴 검사
    for pattern_type, patterns in special_patterns.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                if pattern_type == "인종차별":
                    violations.append({
                        "category": "차별",
                        "keyword": "인종차별 표현",
                        "text": text,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "severity": "높음"
                    })
                elif pattern_type == "편의시설":
                    violations.append({
                        "category": "편의시설 접근권",
                        "keyword": "접근성 문제",
                        "text": text,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "severity": "중간"
                    })
                elif pattern_type == "환경권":
                    violations.append({
                        "category": "주거환경권",
                        "keyword": "환경 문제",
                        "text": text,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "severity": "중간"
                    })
    
    # 기본 키워드 검사
    for category, keywords in HUMAN_RIGHTS_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                violations.append({
                    "category": category,
                    "keyword": keyword,
                    "text": text,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "severity": "보통"
                })
    
    return violations

def generate_ai_response(user_input, violations):
    """AI 응답 생성 (Streamlit Cloud 최적화)"""
    
    # 기본 응답 생성
    if not violations:
        return f"""
안녕하세요! 말씀해주신 내용을 잘 들었어요. 😊

"{user_input}"

지금 상황에서는 특별한 인권 침해 요소가 발견되지 않았어요. 
하지만 언제든지 힘들거나 궁금한 일이 있으면 저에게 말해주세요!

🌟 **함께 생각해볼 점들:**
- 모든 사람은 존중받을 권리가 있어요
- 어려운 일이 있으면 어른에게 도움을 요청하세요
- 여러분의 의견과 감정도 소중해요

더 궁금한 점이 있으면 언제든 물어보세요! 💪
        """
    
    # 인권 침해가 발견된 경우
    violation_types = list(set([v["category"] for v in violations]))
    
    response = f"""
🔍 **말씀해주신 내용을 분석해보니:**
"{user_input}"

다음과 같은 인권과 관련된 중요한 부분들이 있어요:

"""
    
    for violation_type in violation_types:
        law_info = RELATED_LAWS.get(violation_type, {})
        
        # 심각도에 따른 이모지
        severity_emojis = {"높음": "🚨", "중간": "⚠️", "보통": "🔍"}
        violation_data = next((v for v in violations if v["category"] == violation_type), {})
        severity = violation_data.get("severity", "보통")
        
        response += f"""
{severity_emojis[severity]} **{violation_type}** (심각도: {severity})

📋 **관련 법률**: {law_info.get('법률', '관련 법률 정보 없음')}

📝 **쉬운 설명**: {law_info.get('설명', '추가 설명이 필요합니다.')}

💡 **AI의 조언**: 
"""
        
        # 카테고리별 맞춤 조언
        if violation_type == "차별":
            response += "모든 사람은 다르지만 똑같이 소중해요. 차별하거나 차별받는 상황이 있다면 즉시 어른에게 알려주세요."
        elif violation_type == "편의시설 접근권":
            response += "불편한 시설이 있다면 학교나 관리사무소에 개선을 요청할 수 있어요. 모든 사람이 편리하게 이용할 수 있어야 해요."
        elif violation_type == "주거환경권":
            response += "안전하고 즐겁게 놀 수 있는 공간이 필요해요. 어른들에게 놀이터나 안전한 놀이 공간을 만들어달라고 요청해보세요."
        else:
            response += "이런 상황에서는 혼자 해결하려 하지 말고 믿을 만한 어른에게 도움을 요청하는 것이 가장 중요해요."
        
        response += "\n"
    
    response += """

🌟 **꼭 기억하세요:**
- 여러분의 권리는 정말 소중해요
- 힘들 때는 절대 혼자 해결하려 하지 마세요
- 부모님, 선생님, 또는 믿을 만한 어른에게 도움을 요청하세요
- 여러분은 보호받을 권리가 있어요

더 궁금한 점이 있으면 언제든 물어보세요! 🤗
    """
    
    return response

def display_welcome():
    """환영 메시지 및 앱 소개"""
    st.markdown("""
    <div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); 
                padding: 2rem; border-radius: 10px; color: white; text-align: center; margin-bottom: 2rem;">
        <h1>🤖 AI 인권 지킴이 챗봇</h1>
        <h3>초등학생을 위한 똑똑한 인권 교육 도우미</h3>
        <p>일상생활에서 겪는 일들을 자유롭게 말해보세요. AI가 인권과 관련된 부분을 찾아서 도움을 드릴게요!</p>
    </div>
    """, unsafe_allow_html=True)

def display_chat():
    """채팅 인터페이스"""
    display_welcome()
    
    # 사용법 안내
    with st.expander("💡 어떻게 사용하나요?", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.write("""
            **🗣️ 이런 것들을 말해보세요:**
            - 친구들과 있었던 일
            - 학교에서 겪은 어려움  
            - 집이나 동네에서 불편한 점
            - 공정하지 않다고 느낀 일
            """)
        with col2:
            st.write("""
            **🛡️ 안전하게 사용하려면:**
            - 이름, 주소, 전화번호는 말하지 마세요
            - 심각한 문제는 즉시 어른에게 알리세요
            - AI는 조언만 해줄 뿐, 실제 도움은 어른이 해야 해요
            """)
    
    # 예시 버튼들
    st.subheader("🌟 예시를 눌러보세요!")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🖼️ AI가 흑인을 고릴라라고 했어요", use_container_width=True):
            test_input = "AI가 흑인 사진을 보고 고릴라라고 인식했어요"
            handle_user_input(test_input)
    
    with col2:
        if st.button("🚿 세면대가 너무 높아요", use_container_width=True):
            test_input = "학교 화장실 세면대가 너무 높아서 손을 씻기 어려워요"
            handle_user_input(test_input)
    
    with col3:
        if st.button("🏠 놀이터가 없어요", use_container_width=True):
            test_input = "우리 아파트에는 놀이터가 없어서 놀 곳이 없어요"
            handle_user_input(test_input)
    
    st.markdown("---")
    
    # 채팅 기록 표시
    if st.session_state.messages:
        st.subheader("💬 대화 기록")
        
        for i, message in enumerate(st.session_state.messages):
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.write(f"👤 **학생**: {message['content']}")
            else:
                with st.chat_message("assistant"):
                    st.markdown(message["content"])
    
    # 사용자 입력
    user_input = st.chat_input("어떤 일이 있었는지 편하게 말해보세요... 🎤")
    
    if user_input:
        handle_user_input(user_input)

def handle_user_input(user_input):
    """사용자 입력 처리"""
    # 사용자 메시지 추가
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # 인권 침해 분석
    violations = analyze_human_rights_violation(user_input)
    if violations:
        st.session_state.analysis_results.extend(violations)
    
    # AI 응답 생성
    response = generate_ai_response(user_input, violations)
    st.session_state.messages.append({"role": "assistant", "content": response})
    
    # 화면 새로고침
    st.rerun()

def display_analysis():
    """대화 분석 탭"""
    st.header("📊 대화 분석 결과")
    
    if not st.session_state.analysis_results:
        st.info("아직 분석된 대화가 없습니다. 먼저 챗봇과 대화해보세요!")
        st.markdown("### 🧪 테스트해보기")
        st.write("대화 탭에서 예시 버튼들을 눌러보세요!")
        return
    
    # 분석 결과 요약
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("총 분석 메시지", len(st.session_state.analysis_results))
    
    with col2:
        violation_types = len(set([r["category"] for r in st.session_state.analysis_results]))
        st.metric("인권 침해 유형", f"{violation_types}가지")
    
    with col3:
        high_severity = len([r for r in st.session_state.analysis_results if r.get("severity") == "높음"])
        st.metric("높은 심각도", f"{high_severity}건", delta="주의 필요" if high_severity > 0 else None)
    
    # 상세 분석
    st.subheader("🔍 발견된 인권 침해 유형")
    
    violation_counts = {}
    severity_counts = {"높음": 0, "중간": 0, "보통": 0}
    
    for result in st.session_state.analysis_results:
        category = result["category"]
        severity = result.get("severity", "보통")
        
        violation_counts[category] = violation_counts.get(category, 0) + 1
        severity_counts[severity] += 1
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**📋 유형별 발생 횟수:**")
        for category, count in violation_counts.items():
            st.write(f"• {category}: {count}회")
    
    with col2:
        st.write("**⚠️ 심각도별 분포:**")
        for severity, count in severity_counts.items():
            emoji = {"높음": "🚨", "중간": "⚠️", "보통": "🔍"}[severity]
            st.write(f"{emoji} {severity}: {count}회")
    
    # 상세 데이터 테이블
    if st.checkbox("📊 상세 데이터 보기"):
        df = pd.DataFrame(st.session_state.analysis_results)
        st.dataframe(df, use_container_width=True)
    
    # 분석 초기화
    if st.button("🔄 분석 결과 초기화", type="secondary"):
        st.session_state.analysis_results = []
        st.success("분석 결과가 초기화되었습니다!")
        st.rerun()

def display_help():
    """도움말 탭"""
    st.header("ℹ️ 도움말")
    
    tab1, tab2, tab3 = st.tabs(["📖 사용법", "⚖️ 인권 정보", "🚨 도움 요청"])
    
    with tab1:
        st.subheader("📱 이 앱은 어떻게 사용하나요?")
        
        st.write("""
        **1단계: 대화하기** 💬
        - 일상생활에서 겪은 일을 자유롭게 입력하세요
        - 친구와의 갈등, 학교 생활, 가정에서의 문제 등 무엇이든 괜찮아요
        
        **2단계: AI 분석** 🤖  
        - AI가 자동으로 인권과 관련된 부분을 찾아서 알려드려요
        - 관련된 법률과 해결 방법도 쉽게 설명해드려요
        
        **3단계: 결과 확인** 📊
        - '대화 분석' 탭에서 누적된 분석 결과를 확인하세요
        - 어떤 인권 문제가 얼마나 자주 발생하는지 알 수 있어요
        """)
        
        st.subheader("🎯 효과적인 사용 팁")
        st.write("""
        - **구체적으로 설명하세요**: "친구가 나를 놀렸어요" 보다는 "친구가 내 외모를 놀리며 못생겼다고 했어요"가 더 정확한 분석을 받을 수 있어요
        - **감정도 표현하세요**: "기분이 나빴어요", "슬펐어요" 같은 감정 표현도 중요해요
        - **질문도 해보세요**: "이런 상황에서는 어떻게 해야 하나요?" 같은 질문도 좋아요
        """)
    
    with tab2:
        st.subheader("📚 인권이란 무엇인가요?")
        st.write("""
        **인권**은 사람이라면 누구나 태어날 때부터 가지는 소중한 권리예요. 
        나이, 성별, 피부색, 장애 여부와 상관없이 모든 사람이 존중받아야 해요.
        """)
        
        st.subheader("🔍 이 앱이 찾아주는 인권 문제들")
        
        rights_info = {
            "차별": "외모, 피부색, 장애, 가정환경 등으로 다르게 대우받는 것",
            "폭력": "때리기, 밀치기 등 몸을 다치게 하거나 마음을 아프게 하는 행동",
            "사생활 침해": "허락 없이 개인적인 것을 보거나 비밀을 퍼뜨리는 것",
            "교육권": "공부할 권리가 침해되는 상황",
            "표현의 자유": "자신의 생각이나 의견을 말할 권리가 제한되는 것",
            "건강권": "건강하게 살 권리가 침해되는 상황",
            "휴식권": "놀이와 휴식할 권리가 침해되는 것",
            "편의시설 접근권": "키나 장애로 인해 시설을 이용하기 어려운 상황",
            "주거환경권": "안전하고 건강한 환경에서 살 권리가 침해되는 것"
        }
        
        for right, description in rights_info.items():
            with st.expander(f"📖 {right}"):
                st.write(description)
    
    with tab3:
        st.subheader("🚨 위급한 상황일 때")
        st.error("""
        **즉시 도움을 요청하세요!**
        
        이 앱은 교육용 도구입니다. 실제로 위험하거나 심각한 상황에서는 
        반드시 어른에게 도움을 요청하세요.
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("""
            **📞 비상 연락처**
            - **학교폭력신고센터**: 117
            - **아동학대신고센터**: 112
            - **국가인권위원회**: 1331
            - **청소년상담전화**: 1388
            """)
        
        with col2:
            st.write("""
            **👥 도움을 요청할 수 있는 사람들**
            - 부모님 또는 가족
            - 담임선생님 또는 상담선생님
            - 학교 보건선생님
            - 믿을 만한 어른들
            """)
        
        st.success("""
        **기억하세요**: 여러분은 혼자가 아니에요. 
        어려운 일이 있으면 언제든 도움을 요청할 수 있어요!
        """)

def main():
    """메인 앱"""
    # 사이드바 구성
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2921/2921222.png", width=80)
        st.title("🔧 메뉴")
        
        # 탭 선택
        selected_tab = st.radio(
            "원하는 기능을 선택하세요:",
            ["💬 AI와 대화하기", "📊 대화 분석", "ℹ️ 도움말"],
            index=0
        )
        
        st.markdown("---")
        
        # 앱 정보
        st.subheader("📱 앱 정보")
        st.write(f"🗣️ 총 대화: {len(st.session_state.messages) // 2}회")
        st.write(f"🔍 분석 결과: {len(st.session_state.analysis_results)}건")
        
        if st.session_state.analysis_results:
            high_severity = len([r for r in st.session_state.analysis_results if r.get("severity") == "높음"])
            if high_severity > 0:
                st.warning(f"⚠️ 주의 필요: {high_severity}건")
        
        st.markdown("---")
        
        # 개발 정보
        with st.expander("👨‍💻 개발 정보"):
            st.write("""
            **개발 목적**: 초등학교 인권 교육
            **대상**: 초등학교 5학년
            **교과**: 사회 (인권을 존중하는 삶)
            **기술**: Streamlit + AI
            """)
        
        # 피드백
        st.markdown("---")
        st.subheader("💌 피드백")
        feedback = st.text_area("앱을 사용해보니 어떠셨나요?", placeholder="자유롭게 의견을 남겨주세요...")
        if st.button("의견 보내기") and feedback:
            st.success("소중한 의견 감사합니다! 📝")
    
    # 메인 컨텐츠
    if selected_tab == "💬 AI와 대화하기":
        display_chat()
    elif selected_tab == "📊 대화 분석":
        display_analysis()
    else:
        display_help()
    
    # 하단 정보
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.8em;">
        🤖 AI 인권 지킴이 챗봇 | 초등학생 인권 교육용 도구<br>
        ⚠️ 교육 목적으로만 사용하세요. 실제 문제가 있으면 어른에게 도움을 요청하세요.
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
