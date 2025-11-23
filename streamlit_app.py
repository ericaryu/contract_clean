import streamlit as st
import os
import tempfile
import sys

# Streamlit Cloud 배포 시 Secrets를 환경변수로 로드
# 로컬에서는 .env가 사용되고, Cloud에서는 st.secrets가 사용됨
if hasattr(st, "secrets"):
    for key, value in st.secrets.items():
        if key in ["OPENAI_API_KEY", "GCP_CREDENTIALS", "SPREADSHEET_URL"]:
            os.environ[key] = str(value)

# 로컬 환경을 위해 .env 파일 로드 (Streamlit Cloud에서는 무시됨/파일없음)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Add the current directory to sys.path to ensure imports work correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from contract_processor import extract_text_node, analyze_contract_node, ContractData
from sheets_manager import GoogleSheetManager

# Page configuration
st.set_page_config(page_title="계약서 분석기", page_icon="📄")

st.title("📄 계약서 분석기")
st.write("PDF 계약서를 업로드하면 AI가 주요 내용을 분석해줍니다.")

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
            state = {"file_path": tmp_file_path}
            extract_result = extract_text_node(state)
            
            if extract_result.get("raw_text"):
                raw_text = extract_result["raw_text"]
                st.info("텍스트 추출 완료")
                with st.expander("추출된 텍스트 보기"):
                    st.text_area("Raw Text", raw_text, height=200)
                
                # 2. Analyze Contract
                state["raw_text"] = raw_text
                analyze_result = analyze_contract_node(state)
                
                if analyze_result.get("extracted_data"):
                    data = analyze_result["extracted_data"]
                    st.success("분석 완료!")
                    
                    # Display results
                    st.subheader("📊 분석 결과")
                    st.json(data)
                    
                    # Save to Sheets
                    if st.button("구글 시트에 저장"):
                        try:
                            # Load environment variables if needed (assuming env.py handles it or already loaded)
                            from env import SPREADSHEET_URL
                            # Or use the constant from contract_processor if available, but it's better to be safe
                            # Ideally contract_processor should expose it or we pass it.
                            # Let's try to import it or define it. 
                            # contract_processor.py has SPREADSHEET_URL defined.
                            from contract_processor import SPREADSHEET_URL
                            
                            manager = GoogleSheetManager(SPREADSHEET_URL)
                            manager.append_row(data)
                            st.success("구글 시트에 저장되었습니다!")
                        except Exception as e:
                            st.error(f"저장 실패: {e}")
                else:
                    st.error(f"분석 실패: {analyze_result.get('status')}")
            else:
                st.error(f"텍스트 추출 실패: {extract_result.get('status')}")

    # Cleanup: The temp file persists. In a real app, we might want to clean it up.
    # For now, we leave it or clean it up if we want.
    # os.unlink(tmp_file_path) 
