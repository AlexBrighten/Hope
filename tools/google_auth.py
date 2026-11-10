"""Unified Google OAuth 2.0 Authentication Helper for Hope UltraLight:
Provides authenticated Google API client sessions for Gmail, Calendar, and Sheets.
"""

import logging
from typing import Optional
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from config import config

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]


class GoogleAuthManager:
    def __init__(self):
        self.creds_file: Path = config.google_credentials_file
        self.token_file: Path = config.google_token_file
        self._credentials: Optional[Credentials] = None

    def is_configured(self) -> bool:
        return self.creds_file.exists() or self.token_file.exists()

    def get_credentials(self) -> Optional[Credentials]:
        """Obtain valid Google OAuth credentials, refreshing if expired."""
        if self._credentials and self._credentials.valid:
            return self._credentials

        creds = None
        if self.token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_file), SCOPES)
            except Exception as e:
                logger.warning(f"Failed to load existing Google token: {e}")

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                self.token_file.write_text(creds.to_json(), encoding="utf-8")
                self._credentials = creds
                return creds
            except Exception as e:
                logger.warning(f"Failed to refresh Google token: {e}")
                creds = None

        if not creds and self.creds_file.exists():
            try:
                flow = InstalledAppFlow.from_client_secrets_file(str(self.creds_file), SCOPES)
                creds = flow.run_local_server(port=0)
                self.token_file.write_text(creds.to_json(), encoding="utf-8")
                self._credentials = creds
                return creds
            except Exception as e:
                logger.error(f"Google OAuth flow failed: {e}")
                return None

        self._credentials = creds
        return creds


google_auth = GoogleAuthManager()

