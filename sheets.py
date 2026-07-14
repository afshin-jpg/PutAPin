import os
import json
import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
STATE_SHEET = "_state"


def _client():
    creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def _spreadsheet():
    return _client().open_by_key(os.environ["SPREADSHEET_ID"])


def get_lists() -> list[str]:
    sh = _spreadsheet()
    return [ws.title for ws in sh.worksheets() if ws.title != STATE_SHEET]


def create_list(name: str):
    sh = _spreadsheet()
    titles = [ws.title for ws in sh.worksheets()]
    if name not in titles:
        sh.add_worksheet(title=name, rows=1000, cols=1)


def get_items(name: str) -> list[str]:
    sh = _spreadsheet()
    try:
        ws = sh.worksheet(name)
        return [v for v in ws.col_values(1) if v]
    except gspread.WorksheetNotFound:
        return []


def add_item(name: str, item: str):
    sh = _spreadsheet()
    try:
        ws = sh.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=name, rows=1000, cols=1)
    ws.append_row([item])


def remove_item(name: str, index: int) -> str | None:
    sh = _spreadsheet()
    try:
        ws = sh.worksheet(name)
        items = [v for v in ws.col_values(1) if v]
        if index < 0 or index >= len(items):
            return None
        removed = items[index]
        ws.delete_rows(index + 1)
        return removed
    except gspread.WorksheetNotFound:
        return None


def get_active_list(chat_id: int) -> str | None:
    sh = _spreadsheet()
    try:
        ws = sh.worksheet(STATE_SHEET)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=STATE_SHEET, rows=100, cols=2)
    records = ws.get_all_values()
    for row in records:
        if row and str(row[0]) == str(chat_id):
            return row[1] if len(row) > 1 else None
    return None


def set_active_list(chat_id: int, list_name: str):
    sh = _spreadsheet()
    try:
        ws = sh.worksheet(STATE_SHEET)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=STATE_SHEET, rows=100, cols=2)
    records = ws.get_all_values()
    for i, row in enumerate(records):
        if row and str(row[0]) == str(chat_id):
            ws.update_cell(i + 1, 2, list_name)
            return
    ws.append_row([str(chat_id), list_name])
