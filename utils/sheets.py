import gspread
from google.oauth2.service_account import Credentials
from config import GOOGLE_SHEET_ID, WORKSHEET_NAME, CREDS_FILE
import traceback

def search_in_sheet(username: str):
    try:
        # Set up authentication
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        creds = Credentials.from_service_account_file(CREDS_FILE, scopes=scope)
        client = gspread.authorize(creds)
        
        print("Authenticated with service account:", creds.service_account_email)
        sheet = client.open_by_key(GOOGLE_SHEET_ID)
        print(f"Accessing sheet: {sheet.title} (ID: {GOOGLE_SHEET_ID})")
        print("Available worksheets:", [ws.title for ws in sheet.worksheets()])
        
        worksheet = sheet.worksheet(WORKSHEET_NAME)
        print(f"Using worksheet: {worksheet.title}")
        
        try:
            cell = worksheet.find(username, in_column=4)
            row = worksheet.row_values(cell.row)
            return row
        except gspread.exceptions.CellNotFound:
            return None
            
    except gspread.exceptions.APIError as e:
        print(f"Google API Error: {e}")
        return None
    except FileNotFoundError:
        print(f"Credentials file not found: {CREDS_FILE}")
        return None
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        traceback.print_exc()
        return None