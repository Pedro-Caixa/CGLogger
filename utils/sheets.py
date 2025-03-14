import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
CREDS = Credentials.from_service_account_file("creds.json", scopes=SCOPES)

client = gspread.authorize(CREDS)

service = build("sheets", "v4", credentials=CREDS)

sheets = {
    "Main": "1bzZk0w_oxKDkhHOjJ6MQd9D6-SfqG4a1bvRXzj938dY",
    "Officer": "1bzZk0w_oxKDkhHOjJ6MQd9D6-SfqG4a1bvRXzj938dY",
    "Leaderboard": "1bzZk0w_oxKDkhHOjJ6MQd9D6-SfqG4a1bvRXzj938dY"
}

def rgb_to_hex(red, green, blue):
    """Convert RGB values (0-1 range) to a hex color code."""
    r = int(red * 255)
    g = int(green * 255)
    b = int(blue * 255)
    return f"#{r:02x}{g:02x}{b:02x}"

def get_background_color(sheetName, cell_range):
    """Get the background color of a cell in hex format."""
    try:
        spreadsheet_id = sheets[sheetName]
        sheet_metadata = service.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            ranges=[cell_range],
            includeGridData=True
        ).execute()
        
        grid_data = sheet_metadata["sheets"][0]["data"][0]["rowData"][0]["values"][0]
        if "effectiveFormat" in grid_data:
            bg_color = grid_data["effectiveFormat"]["backgroundColor"]
            hex_color = rgb_to_hex(bg_color.get("red", 1), bg_color.get("green", 1), bg_color.get("blue", 1))
            return hex_color
        else:
            return None
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def get_row_by_username(sheetName, username):
    """Find the row containing the username."""
    try:
        spreadsheet = client.open_by_key(sheets[sheetName])
        worksheet = spreadsheet.worksheet("Main Sheet")
        all_values = worksheet.get_all_values()
        
        for row_index, row in enumerate(all_values):
            if username in row:
                return row_index + 1
        print(f"Username '{username}' not found in sheet '{sheetName}'.")
        return None
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def get_cell_color(sheetName, username, column_identifier):
    """
    Get the background color of a cell in the username's row.
    - `column_identifier`: Column name (e.g., "May") or 1-based index (e.g., 5).
    """
    try:
        row_index = get_row_by_username(sheetName, username)
        if not row_index:
            return None
        
        spreadsheet = client.open_by_key(sheets[sheetName])
        worksheet = spreadsheet.worksheet("Main Sheet")
        
        if isinstance(column_identifier, str):
            headers = worksheet.row_values(1)
            try:
                col_index = headers.index(column_identifier) + 1
            except ValueError:
                print(f"Column '{column_identifier}' not found.")
                return None
        else:
            col_index = column_identifier
        
        cell_ref = gspread.utils.rowcol_to_a1(row_index, col_index)
        cell_range = f"Main Sheet!{cell_ref}"
        
        return get_background_color(sheetName, cell_range)
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return None