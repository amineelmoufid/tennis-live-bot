import os
import json
import traceback
from google.oauth2 import service_account
from googleapiclient.discovery import build

SPREADSHEET_ID = '1T6OnZQB8lbaUTpYU-AqNEg7698L2XpfT8h7i-lGXmD0'
SHEET_GID = 1783205692
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_sheets_service():
    """Initializes and returns the Google Sheets API service using env vars."""
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json:
        print("No GOOGLE_CREDENTIALS found in environment.")
        return None
        
    try:
        creds_dict = json.loads(creds_json)
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=SCOPES
        )
        service = build('sheets', 'v4', credentials=creds)
        return service
    except Exception as e:
        print(f"Failed to build Sheets service: {e}")
        return None

def get_sheet_title_from_gid(service, spreadsheet_id, target_gid):
    """Maps the GID to the actual Sheet Title so we can append to it."""
    try:
        sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = sheet_metadata.get('sheets', '')
        for sheet in sheets:
            if sheet.get("properties", {}).get("sheetId") == target_gid:
                return sheet.get("properties", {}).get("title")
    except Exception as e:
        print(f"Error fetching sheet title: {e}")
    return None

def export_prediction_to_sheet(date_str, match_id, matchup, score, selection, market_odds, true_odds, ev_pct):
    """Appends a single prediction row to the target Google Sheet tab."""
    service = get_sheets_service()
    if not service:
        return False
        
    sheet_title = get_sheet_title_from_gid(service, SPREADSHEET_ID, SHEET_GID)
    if not sheet_title:
        print(f"Could not find Sheet Title for GID {SHEET_GID}")
        return False
        
    range_name = f"'{sheet_title}'!A:I"
    
    # We match the columns requested: 
    # [Date, Match ID, Matchup, Score, Selection, Market Odds, True Fair Odds, EV %]
    values = [
        [date_str, match_id, matchup, score, selection, f"{market_odds:.2f}", f"{true_odds:.2f}", f"{ev_pct:.2f}%"]
    ]
    body = {'values': values}
    
    try:
        result = service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        print(f"Appended {result.get('updates').get('updatedCells')} cells to Google Sheets.")
        return True
    except Exception as e:
        print(f"Error appending to Google Sheets: {e}")
        return False
