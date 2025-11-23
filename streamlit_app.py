import streamlit as st
import os
import tempfile
import sys
import pandas as pd
from typing import Any, Dict
from datetime import datetime

# Streamlit Cloud 배포 시 Secrets를 환경변수로 로드
if hasattr(st, "secrets"):
    if "OPENAI_API_KEY" in st.secrets:
        os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]

# 로컬 환경을 위해 .env 파일 로드
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from contract_processor import extract_text_node, analyze_contract_node, AgentState
# ❌ 이 줄 삭제: from sheets_manager import GoogleSheetManager

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
                st.session_state.raw_text = raw_text
                st.info("텍스트 추출 완료")
                
                # 2. Analyze Contract
                state["raw_text"] = raw_text
                agent_state = AgentState(**state)
                analyze_result = analyze_contract_node(agent_state)
                
                if analyze_result.get("extracted_data"):
                    st.session_state.analyzed_data = analyze_result["extracted_data"]
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
        
        # CSV 다운로드 버튼
        data = st.session_state.analyzed_data
        
        # DataFrame 생성
        df = pd.DataFrame([{
            "처리일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "계약명": data.get("contract_name", ""),
            "이용자명": data.get("user_name", ""),
            "계약기간": data.get("contract_period", ""),
            "청구일": data.get("claim_dates", ""),
            "지급비율": data.get("payment_ratios", ""),
            "계약체결일": data.get("contract_sign_date", ""),
            "상호": data.get("company_name", ""),
            "주소": data.get("company_address", ""),
            "사업자번호": data.get("business_registration_number", ""),
            "대표이사": data.get("ceo_name", ""),
            "연락처": data.get("contact", "")
        }])
        
        # CSV 변환
        csv = df.to_csv(index=False, encoding='utf-8-sig')
        
        st.download_button(
            label="📥 CSV 파일로 다운로드",
            data=csv,
            file_name=f"contract_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )