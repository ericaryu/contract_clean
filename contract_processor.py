import os
import tkinter as tk
from tkinter import filedialog
from typing import Optional
from typing_extensions import TypedDict

# PDF 텍스트 추출 로더
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END

# 로컬 모듈
from sheets_manager import GoogleSheetManager

# --- 설정 상수 ---
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1p82-rmbcGuQ4asd15teiSsBn4J41x0rOpIDVQSrPEIU/"

# --- 환경 변수 세팅 ---
# 반드시 Streamlit Cloud 또는 로컬 .env에서 설정되어야 함
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# --- 1. 데이터 구조 정의 ---
class ContractData(BaseModel):
    contract_name: str
    user_name: str
    contract_period: str
    claim_dates: str
    payment_ratios: str
    contract_sign_date: str
    user_business_info: str

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
        full_text = "\n".join([page.page_content for page in pages])

        if not full_text.strip():
            return {"status": "⚠️ 텍스트를 찾을 수 없습니다. (스캔된 이미지 PDF일 가능성 높음)"}

        return {"raw_text": full_text, "status": "텍스트 추출 성공"}

    except Exception as e:
        return {"status": f"❌ PDF 읽기 오류: {str(e)}"}

def analyze_contract_node(state: AgentState):
    raw_text = state.get("raw_text")
    if not raw_text:
        return {"status": "분석할 텍스트 데이터가 없습니다."}

    print("🔍 [AI 분석 중] 계약서 상세 내용을 파악하고 있습니다...")

    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    structured_llm = llm.with_structured_output(ContractData)

    system_prompt = """
    당신은 전문 계약서 분석 AI입니다. 
    입력된 계약서 텍스트를 꼼꼼히 분석하여 다음 정보를 추출하세요:
    1. 계약명
    2. 이용자 (고객사 이름)
    3. 계약기간
    4. 청구일 (대금 지급 시기)
    5. 지급 비율 (선금/잔금 비율 등)
    6. 계약 체결일 (서명란 근처의 날짜)
    7. 이용자의 사업자 정보 (등록번호, 주소 등)
    """

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"다음 계약서 내용을 분석해줘:\n\n{raw_text}")
    ]

    try:
        result: ContractData = structured_llm.invoke(messages)
        print(f"✅ [분석 완료] 계약명: {result.contract_name} / 이용자: {result.user_name}")
        return {"extracted_data": result.dict(), "status": "분석 성공"}
    except Exception as e:
        return {"status": f"❌ AI 분석 실패: {str(e)}"}

def save_to_sheet_node(state: AgentState):
    data = state.get("extracted_data")
    if not data:
        return {"status": "저장할 데이터가 없습니다."}

    print("💾 [저장 중] 구글 스프레드시트에 기록 중...")

    try:
        gs = GoogleSheetManager(spreadsheet_url=SPREADSHEET_URL)
        gs.append_row(data)
        return {"status": "✅ 처리 완료! 스프레드시트를 확인하세요."}
    except Exception as e:
        return {"status": f"❌ 저장 실패: {str(e)}"}

# --- 4. 그래프 연결 ---
def create_workflow():
    workflow = StateGraph(AgentState)
    workflow.add_node("extract_text", extract_text_node)
    workflow.add_node("analyze_contract", analyze_contract_node)
    workflow.add_node("save_to_sheet", save_to_sheet_node)

    workflow.add_edge(START, "extract_text")
    workflow.add_edge("extract_text", "analyze_contract")
    workflow.add_edge("analyze_contract", "save_to_sheet")
    workflow.add_edge("save_to_sheet", END)

    return workflow.compile()

# --- 5. 파일 선택 GUI ---
def select_file():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="분석할 계약서 PDF를 선택하세요",
        filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
    )
    return file_path

# --- 6. 실행부 ---
if __name__ == "__main__":
    print("📂 파일 선택 창을 띄웁니다...")
    selected_path = select_file()

    if selected_path:
        app = create_workflow()
        print(f"🚀 프로세스 시작... (선택된 파일: {selected_path})")

        final_state = app.invoke({"file_path": selected_path})

        print("\n" + "=" * 40)
        print(f"결과: {final_state['status']}")
        print("=" * 40)
    else:
        print("❌ 파일이 선택되지 않았습니다.")
