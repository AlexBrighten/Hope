"""Google Sheets Integration for Hope UltraLight:
Lightweight row appending for lead logging, research findings, and tracking.
"""

import re
import logging
from typing import List, Any
from googleapiclient.discovery import build
from tools.google_auth import google_auth

logger = logging.getLogger(__name__)


def _extract_spreadsheet_id(id_or_url: str) -> str:
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", id_or_url)
    if match:
        return match.group(1)
    return id_or_url.strip()


def _get_sheets_service():
    creds = google_auth.get_credentials()
    if not creds:
        raise RuntimeError("Google OAuth credentials missing. Place `credentials.json` in root folder.")
    return build("sheets", "v4", credentials=creds)


async def sheet_append(spreadsheet_id_or_url: str, range_name: str, values: List[Any]) -> str:
    """Append a row of values to a Google Spreadsheet (e.g. range_name='Sheet1!A1')."""
    try:
        service = _get_sheets_service()
        sheet_id = _extract_spreadsheet_id(spreadsheet_id_or_url)

        # Ensure values is 2D list
        if not isinstance(values[0], list):
            row_data = [values]
        else:
            row_data = values

        body = {"values": row_data}
        result = service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range=range_name,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body
        ).execute()

        updates = result.get("updates", {})
        return f"📊 Appended {updates.get('updatedRows', 1)} row(s) to `{range_name}` in spreadsheet `{sheet_id[:8]}...`"
    except Exception as e:
        logger.error(f"Sheet append error: {e}")
        return f"Failed to append to spreadsheet: {e}"

