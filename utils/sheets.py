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
    try:
        spreadsheet = client.open_by_key(sheets[sheetName])
        
        worksheet = spreadsheet.worksheet("Main Sheet")
        
        all_values = worksheet.get_all_values()
        
        for row_index, row in enumerate(all_values):
            if username in row:
                col_index = row.index(username)
                
                return row_index + 1, col_index + 1, [cell for cell in row if cell.strip()]
        
        print(f"Username '{username}' not found in sheet '{sheetName}'.")
        return None, None, None
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return None, None, None

def get_username_info(sheetName, username):
    row_index, col_index, filtered_row = get_row_by_username(sheetName, username)
    
    if row_index is None or col_index is None:
        return None
    
    cell_range = f"Main Sheet!{gspread.utils.rowcol_to_a1(row_index, col_index)}"
    bg_color = get_background_color(sheetName, cell_range)
    
    return {
        "row_data": filtered_row,
        "background_color": bg_color
    }

username_info = get_username_info("Main", "Bunny112071")
if username_info:
    print("Row Data:", username_info["row_data"])
    print("Background Color (Hex):", username_info["background_color"])
else:
    print("Username not found or an error occurred.")