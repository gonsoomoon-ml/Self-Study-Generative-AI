import streamlit as st
import uuid
import boto3
from datetime import datetime
import json
import time
import requests
from PIL import Image
import plotly.express as px
import pandas as pd
import sys
import os

# 프로젝트 경로 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'use_cases/customer_support/notebooks'))

# 기존 에이전트 구성 요소
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from bedrock_agentcore.memory import MemoryClient
from mcp.client.streamable_http import streamablehttp_client

# Lab 1-4에서 만든 모듈들
from lab_helpers.lab1_strands_agent import (
    ECOMMERCE_SYSTEM_PROMPT as SYSTEM_PROMPT,
    check_return_eligibility,
    process_return_request,
    get_product_recommendations,
    ECOMMERCE_MODEL_ID as MODEL_ID
)
from lab_helpers.ecommerce_memory import (
    EcommerceCustomerMemoryHooks,
    create_or_get_ecommerce_memory_resource
)
from lab_helpers.utils import get_ssm_parameter, get_cognito_client_secret

# Lab 3에서 만든 추가 도구들
sys.path.insert(0, os.path.join(project_root, 'use_cases/customer_support'))
from tools.return_tools import process_return
from tools.exchange_tools import process_exchange
from tools.search_tools import web_search

# 페이지 설정
st.set_page_config(
    page_title="K-Style 고객센터",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 한국어 CSS 스타일링
st.markdown("""
<style>
.main-header {
    font-size: 2.5rem;
    font-weight: bold;
    color: #2E3440;
    text-align: center;
    margin-bottom: 1rem;
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.chat-container {
    background-color: #f8f9fa;
    border-radius: 10px;
    padding: 20px;
    margin: 10px 0;
}

.customer-message {
    background-color: #007bff;
    color: white;
    padding: 10px 15px;
    border-radius: 18px;
    margin: 5px 0;
    max-width: 70%;
    margin-left: auto;
}

.agent-message {
    background-color: #e9ecef;
    color: #2E3440;
    padding: 10px 15px;
    border-radius: 18px;
    margin: 5px 0;
    max-width: 70%;
}

.sidebar-info {
    background-color: #f1f3f4;
    padding: 15px;
    border-radius: 10px;
    margin: 10px 0;
}

.quick-action-btn {
    background-color: #667eea;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 5px;
    margin: 5px;
    cursor: pointer;
    transition: all 0.3s;
}

.quick-action-btn:hover {
    background-color: #5a6fcf;
    transform: translateY(-2px);
}

/* 한국어 폰트 지원 */
.stMarkdown, .stText {
    font-family: 'Noto Sans KR', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# 에이전트 초기화 함수
@st.cache_resource
def initialize_agent():
    """에이전트를 초기화합니다."""
    try:
        REGION = boto3.session.Session().region_name
        
        # Bedrock 모델
        model = BedrockModel(
            model_id=MODEL_ID,
            temperature=0.3,
            region_name=REGION
        )
        
        # 메모리 클라이언트
        memory_client = MemoryClient(region_name=REGION)
        memory_id = create_or_get_ecommerce_memory_resource()
        
        # MCP 클라이언트 설정 (Gateway 통합)
        try:
            # Gateway 정보 가져오기
            gateway_id = get_ssm_parameter("/app/ecommerce/agentcore/gateway_id")
            client_id = get_ssm_parameter("/app/customersupport/agentcore/machine_client_id")
            client_secret = get_cognito_client_secret()
            scope = get_ssm_parameter("/app/customersupport/agentcore/cognito_auth_scope")
            token_url = get_ssm_parameter("/app/customersupport/agentcore/cognito_token_url")
            
            # 토큰 요청
            token_response = requests.post(
                token_url,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "scope": scope,
                }
            )
            
            gateway_access_token = token_response.json()["access_token"]
            
            # Gateway URL 가져오기
            gateway_client = boto3.client("bedrock-agentcore-control", region_name=REGION)
            gateway_response = gateway_client.get_gateway(gatewayIdentifier=gateway_id)
            gateway_url = gateway_response["gatewayUrl"]
            
            # MCP 클라이언트 생성
            mcp_client = MCPClient(
                lambda: streamablehttp_client(
                    gateway_url,
                    headers={"Authorization": f"Bearer {gateway_access_token}"},
                )
            )
            mcp_client.start()
            mcp_tools = mcp_client.list_tools_sync()
            
        except Exception as e:
            st.warning(f"Gateway 연결 실패 (로컬 도구만 사용): {str(e)}")
            mcp_tools = []
        
        # 도구 결합
        tools = [
            process_return,
            process_exchange, 
            web_search,
        ] + mcp_tools
        
        return model, memory_client, memory_id, tools
        
    except Exception as e:
        st.error(f"에이전트 초기화 실패: {str(e)}")
        return None, None, None, []

# 세션 상태 초기화
def initialize_session_state():
    """Streamlit 세션 상태를 초기화합니다."""
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    
    if "customer_id" not in st.session_state:
        st.session_state.customer_id = "customer_streamlit_001"
    
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "안녕하세요! K-Style 고객센터에 오신 것을 환영합니다! 🛍️\n\n패션과 뷰티 관련하여 도움이 필요한 사항이 있으시면 언제든 말씀해 주세요. 반품, 교환, 스타일링 조언 등 무엇이든 도와드리겠습니다!",
                "timestamp": datetime.now().strftime("%H:%M")
            }
        ]
    
    if "customer_info" not in st.session_state:
        st.session_state.customer_info = {
            "name": "김고객",
            "vip_level": "골드",
            "total_orders": 15,
            "favorite_categories": ["원피스", "아우터", "스킨케어"],
            "preferred_brands": ["ZARA", "이니스프리", "에이블리"]
        }

# 빠른 액션 버튼들
def render_quick_actions():
    """빠른 액션 버튼들을 렌더링합니다."""
    st.markdown("### 🚀 빠른 서비스")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📦 반품 신청", key="quick_return"):
            quick_message = "반품을 신청하고 싶어요. 도와주세요."
            st.session_state.messages.append({
                "role": "user",
                "content": quick_message,
                "timestamp": datetime.now().strftime("%H:%M")
            })
            st.rerun()
    
    with col2:
        if st.button("🔄 교환 신청", key="quick_exchange"):
            quick_message = "사이즈 교환을 하고 싶어요."
            st.session_state.messages.append({
                "role": "user",
                "content": quick_message,
                "timestamp": datetime.now().strftime("%H:%M")
            })
            st.rerun()
    
    with col3:
        if st.button("💄 스타일링 조언", key="quick_styling"):
            quick_message = "이번 시즌 트렌드 코디 방법을 알려주세요."
            st.session_state.messages.append({
                "role": "user",
                "content": quick_message,
                "timestamp": datetime.now().strftime("%H:%M")
            })
            st.rerun()

# 고객 정보 사이드바
def render_customer_sidebar():
    """고객 정보 사이드바를 렌더링합니다."""
    with st.sidebar:
        st.markdown("## 👤 고객 정보")
        
        info = st.session_state.customer_info
        
        st.markdown(f"**이름:** {info['name']}")
        st.markdown(f"**VIP 등급:** {info['vip_level']} ⭐")
        st.markdown(f"**총 주문 수:** {info['total_orders']}회")
        
        st.markdown("**선호 카테고리:**")
        for category in info['favorite_categories']:
            st.markdown(f"• {category}")
        
        st.markdown("**선호 브랜드:**")
        for brand in info['preferred_brands']:
            st.markdown(f"• {brand}")
        
        st.markdown("---")
        
        # 최근 주문 정보
        st.markdown("## 📋 최근 주문")
        
        recent_orders = [
            {"order_number": "KS-2024-001234", "item": "플라워 패턴 원피스", "status": "배송완료"},
            {"order_number": "KS-2024-001235", "item": "쿠션 파운데이션", "status": "배송중"},
            {"order_number": "KS-2024-001236", "item": "니트 가디건", "status": "주문완료"}
        ]
        
        for order in recent_orders:
            with st.container():
                st.markdown(f"**{order['order_number']}**")
                st.markdown(f"• {order['item']}")
                st.markdown(f"• 상태: {order['status']}")
                st.markdown("")
        
        # 고객 만족도
        st.markdown("---")
        st.markdown("## 📊 서비스 통계")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("고객 만족도", "4.8/5.0", "0.2")
        with col2:
            st.metric("평균 응답시간", "1.2초", "-0.3초")

# 메인 채팅 인터페이스
def render_chat_interface():
    """메인 채팅 인터페이스를 렌더링합니다."""
    
    # 채팅 메시지 표시
    chat_container = st.container()
    
    with chat_container:
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.markdown(
                    f"""<div style="text-align: right; margin: 10px 0;">
                    <div class="customer-message" style="display: inline-block; background-color: #007bff; color: white; padding: 10px 15px; border-radius: 18px; max-width: 70%;">
                    {message["content"]}
                    </div>
                    <div style="font-size: 0.8em; color: #666; margin-top: 5px;">{message["timestamp"]}</div>
                    </div>""",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"""<div style="text-align: left; margin: 10px 0;">
                    <div class="agent-message" style="display: inline-block; background-color: #e9ecef; color: #2E3440; padding: 10px 15px; border-radius: 18px; max-width: 70%;">
                    🤖 {message["content"]}
                    </div>
                    <div style="font-size: 0.8em; color: #666; margin-top: 5px;">{message["timestamp"]}</div>
                    </div>""",
                    unsafe_allow_html=True
                )

# 에이전트 응답 생성 (실제 스트리밍)
def get_agent_response_streaming(user_input, model, memory_client, memory_id, tools):
    """에이전트로부터 스트리밍 응답을 받아옵니다."""
    try:
        # 메모리 훅스 생성
        memory_hooks = EcommerceCustomerMemoryHooks(
            memory_id, 
            memory_client, 
            st.session_state.customer_id, 
            st.session_state.session_id
        )
        
        # 에이전트 생성
        agent = Agent(
            model=model,
            tools=tools,
            hooks=[memory_hooks],
            system_prompt=SYSTEM_PROMPT
        )
        
        # 모델에서 직접 스트리밍 시도
        try:
            # Agent의 run_step으로 스트리밍 시도
            messages = [{"role": "user", "content": user_input}]
            
            # 모델 직접 호출로 스트리밍
            for chunk in model.stream(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_input}
                ]
            ):
                if hasattr(chunk, 'content') and chunk.content:
                    yield chunk.content
                elif hasattr(chunk, 'text'):
                    yield chunk.text
                elif isinstance(chunk, str):
                    yield chunk
                elif hasattr(chunk, 'delta') and hasattr(chunk.delta, 'text'):
                    yield chunk.delta.text
                    
        except Exception as stream_error:
            # 스트리밍 실패 시 일반 응답으로 폴백하고 시뮬레이션
            response = agent(user_input)
            
            # 응답 텍스트 추출
            if hasattr(response, 'message') and 'content' in response.message:
                content = response.message['content'][0]['text']
            elif hasattr(response, 'content'):
                content = response.content
            else:
                content = str(response)
            
            # 단어 단위로 스트리밍 시뮬레이션
            words = content.split(' ')
            for word in words:
                yield word + " "
                
    except Exception as e:
        yield f"죄송합니다. 일시적인 오류가 발생했습니다: {str(e)}"

# 메인 애플리케이션
def main():
    """메인 애플리케이션 함수"""
    
    # 세션 상태 초기화
    initialize_session_state()
    
    # 헤더
    st.markdown(
        '<h1 class="main-header">🛍️ K-Style 고객센터</h1>',
        unsafe_allow_html=True
    )
    
    st.markdown(
        '<p style="text-align: center; color: #666; font-size: 1.1em;">패션 & 뷰티 전문 AI 상담사가 24시간 도움을 드립니다</p>',
        unsafe_allow_html=True
    )
    
    # 에이전트 초기화
    with st.spinner("AI 상담사 준비 중..."):
        model, memory_client, memory_id, tools = initialize_agent()
    
    if model is None:
        st.error("에이전트 초기화에 실패했습니다. 관리자에게 문의해주세요.")
        return
    
    # 레이아웃 구성
    render_customer_sidebar()
    
    # 빠른 액션 버튼
    render_quick_actions()
    
    st.markdown("---")
    
    # 채팅 인터페이스
    st.markdown("### 💬 상담 채팅")
    
    # 채팅 메시지 표시
    render_chat_interface()
    
    # 사용자 입력
    user_input = st.chat_input("메시지를 입력하세요... (예: 반품하고 싶어요, 스타일링 조언 부탁드려요)")
    
    if user_input:
        # 사용자 메시지 추가
        st.session_state.messages.append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().strftime("%H:%M")
        })
        
        # 스트리밍 응답 표시 (세션에 미리 저장하지 않음)
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            # 스트리밍 진행 중임을 표시
            message_placeholder.markdown("🤖 답변을 생성하고 있습니다...")
            
            for chunk in get_agent_response_streaming(user_input, model, memory_client, memory_id, tools):
                full_response += chunk
                # 커서 효과와 함께 실시간 업데이트
                message_placeholder.markdown(full_response + "▌")
                time.sleep(0.05)  # 조금 더 긴 딜레이로 스트리밍 효과 강화
            
            # 최종 응답 표시 (커서 제거)
            message_placeholder.markdown(full_response)
        
        # 스트리밍 완료 후 세션에 저장
        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response,
            "timestamp": datetime.now().strftime("%H:%M")
        })
    
    # 푸터
    st.markdown("---")
    st.markdown(
        "<p style='text-align: center; color: #888; font-size: 0.9em;'>🤖 Amazon Bedrock AgentCore 기반 • 🛨 24시간 서비스 • 📞 추가 문의: 1588-1234</p>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()