import sys, os
import streamlit as st
import pandas as pd
from pathlib import Path
import glob
import base64

module_path = ".."
sys.path.append(os.path.abspath(module_path))
os.environ['LLM_MODULE'] = 'src.agents.llm_st'

from main import execution
from src.config.agents import AGENT_LLM_MAP

##################### Configuration ########################
UPLOAD_DIR = "./uploaded_files/"  # CSV 파일 저장 디렉토리
Path(UPLOAD_DIR).mkdir(exist_ok=True)  # 디렉토리 생성

##################### Title ########################
st.set_page_config(page_title="Amazon Bedrock-Manus: Agentic Deep Report Generation💬", page_icon="💬", layout="wide")
st.markdown("""
<div style='text-align: left;'>
<h1 style='margin: 0; padding: 0; line-height: 1.2;'>Amazon Bedrock-Manus Powered:</h1>
<h1 style='margin: 0; padding: 0; line-height: 1.2;'>Agentic Deep Data Analysis & Report Generation</h1>
</div>
""", unsafe_allow_html=True)


####################### Initialization ###############################
if "messages" not in st.session_state: 
    st.session_state["messages"] = []
if "history_ask" not in st.session_state: 
    st.session_state["history_ask"] = []
if "history_answer" not in st.session_state: 
    st.session_state["history_answer"] = []
if "ai_results" not in st.session_state: 
    st.session_state["ai_results"] = {"coordinator": {}, "planner": {}, "supervisor": {}, "coder": {}, "reporter": {}}
if "current_agent" not in st.session_state: 
    st.session_state["current_agent"] = ""
if "uploaded_file_path" not in st.session_state: 
    st.session_state["uploaded_file_path"] = None

####################### File Upload Section ###############################
st.sidebar.header("📁 CSV 파일 업로드")
uploaded_file = st.sidebar.file_uploader(
    "CSV 파일을 선택하세요", 
    type=['csv'],
    help="분석할 CSV 파일을 업로드하세요"
)

if uploaded_file is not None:
    # 파일 저장
    file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    abs_file_path = os.path.abspath(file_path)
    st.session_state["uploaded_file_path"] = abs_file_path
    
    # 파일 미리보기
    st.sidebar.success(f"✅ 파일 업로드 완료: {uploaded_file.name}")
    
    try:
        df = pd.read_csv(abs_file_path)
        st.sidebar.write("**데이터 미리보기:**")
        st.sidebar.dataframe(df.head(), use_container_width=True)
        st.sidebar.write(f"📊 행 수: {len(df)}, 열 수: {len(df.columns)}")
    except Exception as e:
        st.sidebar.error(f"파일 읽기 오류: {e}")

####################### Application ###############################
# CSV 파일이 업로드된 경우에만 채팅 활성화
if st.session_state["uploaded_file_path"]:
    if user_input := st.chat_input("CSV 데이터에 대해 질문하세요 (예: '매출 추이를 보여줘', '상위 10개 제품 분석해줘')"):
        st.chat_message("user").write(user_input)
        st.session_state["recent_ask"] = user_input
        
        node_names = ["reporter"]
        node_descriptions = {
            "reporter": "CSV 데이터 분석 결과 해석 및 보고서 작성"
        }
        
        # 응답 프로세스 시작
        with st.chat_message("assistant"):
            with st.spinner('CSV 데이터 분석 중...'):
                try:
                    exe_results = execution(
                        user_query=user_input,
                        csv_file_path=st.session_state["uploaded_file_path"]
                    )
                    st.success("✅ 분석이 완료되었습니다!")
                    
                    # PDF 결과 파일 미리보기 기능
                    artifacts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "artifacts"))
                    pdf_files = glob.glob(os.path.join(artifacts_dir, '*.pdf'))
                    
                    if pdf_files:
                        st.markdown("---")
                        st.subheader("📂 PDF 결과 파일 미리보기")
                        for file_name in pdf_files:
                            file_path = os.path.join(artifacts_dir, file_name)
                            st.markdown(f"**{file_name}**")
                            
                            with open(file_path, "rb") as f:
                                base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="900" type="application/pdf"></iframe>'
                            st.markdown("미리보기:")
                            st.markdown(pdf_display, unsafe_allow_html=True)
                    else:
                        st.info("아직 생성된 PDF 결과 파일이 없습니다.")
                    
                except Exception as e:
                    st.error(f"분석 중 오류 발생: {e}")

else:
    # CSV 파일이 업로드되지 않은 경우
    st.info("📋 먼저 사이드바에서 CSV 파일을 업로드해주세요.")
    st.chat_input("CSV 파일을 먼저 업로드하세요", disabled=True)

####################### Footer ###############################
st.sidebar.markdown("---")
st.sidebar.markdown("💡 **사용 방법:**")
st.sidebar.markdown("1. CSV 파일 업로드")
st.sidebar.markdown("2. 데이터에 대한 질문 입력")
st.sidebar.markdown("3. AI 분석 결과 확인")