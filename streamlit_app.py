import streamlit as st
import os
import tempfile
import sys
from typing import Any, Dict

# Streamlit Cloud 배포 시 Secrets를 환경변수로 로드
if hasattr(st, "secrets"):
    for key, value in st.secrets.items():
        if key in ["OPENAI_API_KEY", "GCP_CREDENTIALS", "SPREADSHEET_URL"]:
            os.environ[key] = str(value)

# 로컬 환경을 위해 .env 파일 로드
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from contract_processor import extract_text_node, analyze_contract_node, AgentState
from sheets_manager import GoogleSheetManager

# Page configuration
st.set_page_config(page_title="계약서 분석기", page_icon="📄")

st.title("📄 계약서 분석기")
st.write("PDF 계약서를 업로드하면 AI가 주요 내용을 분석해줍니다.")

# Initialize session state
if "analyzed_data" not in st.session_state:
    st.session_state.analyzed_data = None
if "raw_text" not in st.session_state:
    st.session_state.raw_text = None

# File uploader
uploaded_file = st.file_uploader("계약서 PDF 파일 업로드", type="pdf")

if uploaded_file is not None:
    # Save uploaded file to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_file_path = tmp_file.name
    
    st.success(f"파일 업로드 성공: {uploaded_file.name}")
    
    # Process the file
    if st.button("분석 시작"):
        with st.spinner("텍스트 추출 및 분석 중..."):
            # 1. Extract Text
            state: Dict[str, Any] = {"file_path": tmp_file_path}
            
            agent_state = AgentState(**state)
            extract_result = extract_text_node(agent_state)
            
            if extract_result.get("raw_text"):
                raw_text = extract_result["raw_text"]
                st.session_state.raw_text = raw_text  # Save to session state
                st.info("텍스트 추출 완료")
                
                # 2. Analyze Contract
                state["raw_text"] = raw_text
                agent_state = AgentState(**state)
                analyze_result = analyze_contract_node(agent_state)
                
                if analyze_result.get("extracted_data"):
                    st.session_state.analyzed_data = analyze_result["extracted_data"]  # Save to session state
                    st.success("분석 완료!")
                else:
                    st.error(f"분석 실패: {analyze_result.get('status')}")
            else:
                st.error(f"텍스트 추출 실패: {extract_result.get('status')}")
    
    # Display results if analysis is done
    if st.session_state.analyzed_data:
        st.subheader("📊 분석 결과")
        st.json(st.session_state.analyzed_data)
        
        # Show extracted text
        if st.session_state.raw_text:
            with st.expander("추출된 텍스트 보기"):
                st.text_area("Raw Text", st.session_state.raw_text, height=200)
        
        # Save to Sheets button (now outside the analyze button)
        if st.button("구글 시트에 저장"):
            try:
                spreadsheet_url = os.environ.get("SPREADSHEET_URL", "")
                if not spreadsheet_url:
                    st.error("SPREADSHEET_URL이 설정되지 않았습니다.")
                else:
                    with st.spinner("구글 시트에 저장 중..."):
                        manager = GoogleSheetManager(spreadsheet_url)
                        manager.append_row(st.session_state.analyzed_data)
                        st.success("✅ 구글 시트에 저장되었습니다!")
            except Exception as e:
                st.error(f"❌ 저장 실패: {e}")
                st.exception(e)  # 상세 에러 표시