import gspread
import json
import os
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

class GoogleSheetManager:
    def __init__(self, spreadsheet_url: str):
        self.scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        try:
            # 환경변수에서 GCP 서비스 계정 JSON 문자열 불러오기
            json_str = os.environ["GCP_CREDENTIALS"]
            creds_dict = json.loads(json_str)
            
            # JSON 딕셔너리를 자격증명 객체로 변환
            self.creds = ServiceAccountCredentials.from_json_keyfile_dict(
                creds_dict, self.scope
            )
            
            # Google Sheets 연결
            self.client = gspread.authorize(self.creds)
            self.sheet = self.client.open_by_url(spreadsheet_url).sheet1
        except Exception as e:
            print(f"구글 시트 연결 오류: {e}")
            raise e
    
    def append_row(self, data: dict):
        """
        딕셔너리 데이터를 받아 시트의 다음 행에 추가합니다.
        [처리일시, 계약명, 이용자, 계약기간, 청구일, 지급비율, 계약일, 상호, 주소, 사업자번호, 대표이사, 연락처]
        """
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            data.get("contract_name", ""),
            data.get("user_name", ""),
            data.get("contract_period", ""),
            data.get("claim_dates", ""),
            data.get("payment_ratios", ""),
            data.get("contract_sign_date", ""),
            data.get("company_name", ""),  # 상호
            data.get("company_address", ""),  # 주소
            data.get("business_registration_number", ""),  # 사업자등록번호
            data.get("ceo_name", ""),  # 대표이사
            data.get("contact", "")  # 연락처
        ]
        
        self.sheet.append_row(row)
        return True