import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
CREDS = Credentials.from_service_account_file("creds.json", scopes=SCOPES)
MAIN_SHEET_HEADER_ROWS = [15, 45, 90, 154] 

def update_officer_stat(worksheet, row_index, header_name, amount, is_add=True):
    """Helper function to update a numeric stat for an officer in the given column.
    
    - If `is_add` is True, it adds the amount.
    - If `is_add` is False, it subtracts the amount but ensures the value doesn't go below zero.
    """
    try:
        col_index = get_column_index(worksheet, row_index, header_name)
        if not col_index:
            print(f"Header '{header_name}' not found")
            return False
        
        current_value = worksheet.cell(row_index, col_index).value
        try:
            new_value = int(current_value)
        except (ValueError, TypeError):
            new_value = 0

        if is_add:
            new_value += amount
        else:
            new_value = max(0, new_value - amount)

        worksheet.update_cell(row_index, col_index, new_value)
        return True
    except Exception as e:
        print(f"Error updating '{header_name}': {e}")
        return False

def find_user_sheet(username):
    """
    Search for the given username in the Officer and Main sheets.
    Returns:
        - "Officer" if the user is found in the Officer Sheet.
        - "Main" if the user is not in the Officer Sheet but is found in the Main Sheet.
        - None if the user is not found in either sheet.
    """
    sheet_priority = [
        ("Officer", "Officer Sheet"),
        ("Main", "Main Sheet")
    ]
    
    for key, worksheet_name in sheet_priority:
        try:
            spreadsheet = client.open_by_key(sheets[key])
            worksheet = spreadsheet.worksheet(worksheet_name)
            all_values = worksheet.get_all_values()
            for row in all_values:
                if username in row:
                    return key
        except Exception as e:
            print(f"Error checking sheet {key}: {e}")
    return None


def get_column_index(worksheet, user_row, header_name):
    """Find column index for a header in the nearest header row above the user's row."""
    try:
        header_row = max([hr for hr in MAIN_SHEET_HEADER_ROWS if hr <= user_row])
        
        headers = worksheet.row_values(header_row)
        return headers.index(header_name) + 1
    except (ValueError, KeyError):
        print(f"Header '{header_name}' not found in row {header_row}")
        return None
    except Exception as e:
        print(f"Error finding column: {e}")
        return None

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
    """Find the row containing the username in the given sheet.
    
    For example:
      - If sheetName is "Officer", the worksheet "Officer Sheet" is used.
      - If sheetName is "Main", the worksheet "Main Sheet" is used.
    """
    try:
        spreadsheet = client.open_by_key(sheets[sheetName])

        if sheetName.lower() == "officer":
            worksheet_name = "Officer Sheet"
        else:
            worksheet_name = "Main Sheet"
            
        worksheet = spreadsheet.worksheet(worksheet_name)
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
    
def add_ep(username, amount):
    """Add EP to a user's total with dynamic column detection"""
    try:
        spreadsheet = client.open_by_key(sheets["Main"])
        worksheet = spreadsheet.worksheet("Main Sheet")
        
        row_index = get_row_by_username("Main", username)
        if not row_index:
            print(f"User {username} not found")
            return False
            
        ep_col = get_column_index(worksheet, row_index, "EP")
        if not ep_col:
            return False
            
        current_value = worksheet.cell(row_index, ep_col).value
        try:
            new_value = int(current_value) + amount
        except (ValueError, TypeError):
            new_value = amount
            
        worksheet.update_cell(row_index, ep_col, new_value)
        return True
        
    except Exception as e:
        return False

def remove_ep(username, amount):
    """Remove EP from a user's total with dynamic column detection"""
    try:
        spreadsheet = client.open_by_key(sheets["Main"])
        worksheet = spreadsheet.worksheet("Main Sheet")
        
        row_index = get_row_by_username("Main", username)
        if not row_index:
            return False
            
        ep_col = get_column_index(worksheet, row_index, "EP")
        if not ep_col:
            return False
            
        current_value = worksheet.cell(row_index, ep_col).value
        try:
            current_ep = int(current_value)
        except (ValueError, TypeError):
            current_ep = 0
            
        new_value = max(0, current_ep - amount)
        worksheet.update_cell(row_index, ep_col, new_value)
        return True
        
    except Exception as e:
        return False

def get_ep(username):
    """Get the EP value of a user with dynamic column detection"""
    try:
        spreadsheet = client.open_by_key(sheets["Main"])
        worksheet = spreadsheet.worksheet("Main Sheet")
        
        row_index = get_row_by_username("Main", username)
        if not row_index:
            return None
            
        ep_col = get_column_index(worksheet, row_index, "EP")
        if not ep_col:
            return None
            
        current_value = worksheet.cell(row_index, ep_col).value
        try:
            current_ep = int(current_value)
        except (ValueError, TypeError):
            current_ep = 0
            
        return current_ep
        
    except Exception as e:
        return None
    
def add_events_hosted(username, amount, event_type):
    """Add event-hosting points (OP) to an officer's total."""
    try:
        spreadsheet = client.open_by_key(sheets["Officer"])
        worksheet = spreadsheet.worksheet("Officer Sheet")
        
        row_index = get_row_by_username("Officer", username)
        if not row_index:
            print(f"User {username} not found in Officer sheet")
            return False
        
        update_officer_stat(worksheet, row_index, "OP", amount)

        event_columns = {
            "Company": "Company Events Hosted",
            "Wide": "Events Hosted"
        }
        
        if event_type in event_columns:
            update_officer_stat(worksheet, row_index, event_columns[event_type], amount)

        return True
    except Exception as e:
        print(f"Error in add_events_hosted: {e}")
        return False


def remove_events_hosted(username, amount, event_type):
    """Remove event-hosting points (OP) from an officer's total."""
    try:
        spreadsheet = client.open_by_key(sheets["Officer"])
        worksheet = spreadsheet.worksheet("Officer Sheet")
        
        row_index = get_row_by_username("Officer", username)
        if not row_index:
            print(f"User {username} not found in Officer sheet")
            return False
        
        # Remove OP points
        update_officer_stat(worksheet, row_index, "OP", amount, is_add=False)

        # Remove event-specific column values
        event_columns = {
            "Company": "Company Events Hosted",
            "Wide": "Events Hosted"
        }
        
        if event_type in event_columns:
            update_officer_stat(worksheet, row_index, event_columns[event_type], amount, is_add=False)

        return True
    except Exception as e:
        print(f"Error in remove_events_hosted: {e}")
        return False