import sys
import os
from typing import Optional
from typing_extensions import TypedDict

# 🔥 Streamlit에서 import 오류 안 나도록 상위 경로 자동 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# PDF 텍스트 추출
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel
from langgraph.graph import StateGraph, START, END

# ❌ 이 부분 삭제 - 사용하지 않음
# try:
#     from .sheets_manager import GoogleSheetManager
# except ImportError:
#     from sheets_manager import GoogleSheetManager

# --- 설정 상수 ---
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1p82-rmbcGuQ4asd15teiSsBn4J41x0rOpIDVQSrPEIU/"

# --- 환경 변수 세팅 ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if OPENAI_API_KEY:
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY


# --- 1. 데이터 구조 정의 ---
class ContractData(BaseModel):
    contract_name: str
    user_name: str
    contract_period: str
    claim_dates: str
    payment_ratios: str
    contract_sign_date: str
    company_name: str  # 상호
    company_address: str  # 주소
    business_registration_number: str  # 사업자등록번호
    ceo_name: str  # 대표이사
    contact: str  # 연락처


# --- 2. 상태 정의 ---
class AgentState(TypedDict):
    file_path: str
    raw_text: Optional[str]
    extracted_data: Optional[dict]
    status: str


# --- 3. 주요 노드 함수 ---
def extract_text_node(state: AgentState):
    file_path = state["file_path"]
    print(f"📄 [읽는 중] PDF 텍스트 추출 시작: {file_path}")

    if not os.path.exists(file_path):
        return {"status": "❌ 파일을 찾을 수 없습니다."}

    try:
        loader = PyPDFLoader(file_path)
        pages = loader.load()
        full_text = "\n".join([p.page_content for p in pages])

        if not full_text.strip():
            return {"status": "⚠️ 텍스트가 없습니다. (스캔본일 수 있음)"}

        return {"raw_text": full_text, "status": "텍스트 추출 성공"}

    except Exception as e:
        return {"status": f"❌ PDF 읽기 오류: {str(e)}"}


def analyze_contract_node(state: AgentState):
    raw_text = state.get("raw_text")
    if not raw_text:
        return {"status": "분석할 텍스트가 없습니다."}

    print("🔍 [AI 분석 중] 계약 내용을 파악하고 있습니다...")

    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    structured_llm = llm.with_structured_output(ContractData)

    system_prompt = """
    당신은 전문 계약서 분석 AI입니다.
    입력된 계약서에서 다음 정보를 추출하세요:
    1. contract_name: 계약명
    2. user_name: 이용자명
    3. contract_period: 계약기간
    4. claim_dates: 청구일 (대금 지급 시기)
    5. payment_ratios: 지급 비율 (선금/잔금 등)
    6. contract_sign_date: 계약 체결일
    7. company_name: 이용자의 회사명(상호)
    8. company_address: 이용자의 회사 주소
    9. business_registration_number: 이용자의 사업자등록번호
    10. ceo_name: 이용자의 대표이사 이름
    11. contact: 이용자의 연락처 (이메일, 전화번호 등)
    
    각 필드는 간결하게 추출하고, 없는 정보는 "정보 없음"으로 표시하세요.
    """

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"다음 계약서 내용을 분석해줘:\n\n{raw_text}")
    ]

    try:
        result = structured_llm.invoke(messages)
        print(f"✅ 분석 완료: 계약명={result.contract_name}")
        return {"extracted_data": result.dict(), "status": "분석 성공"}
    except Exception as e:
        return {"status": f"❌ 계약 분석 오류: {str(e)}"}