"""Standalone Google OAuth 2.0 Authorization Script for Hope UltraLight:
Run this on your desktop to authorize Gmail, Calendar, and Sheets in one click.
Saves credentials to token.json for headless 24/7 background operation.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.google_auth import google_auth, SCOPES
from config import config
from google_auth_oauthlib.flow import InstalledAppFlow


def main():
    print("=" * 65)
    print("🌟 Hope UltraLight — Google Workspace OAuth Authorization")
    print("=" * 65)

    creds_file = config.google_credentials_file
    if not creds_file.exists():
        print(f"\n❌ Error: '{creds_file.name}' not found in the Hope root directory.")
        print("\nPlease follow these quick steps to get credentials.json:")
        print("1. Go to Google Cloud Console (https://console.cloud.google.com/)")
        print("2. Enable Gmail API, Google Calendar API, and Google Sheets API.")
        print("3. Create an OAuth 2.0 Client ID (Application type: Desktop App).")
        print("4. Download the JSON and save it as 'credentials.json' in D:\\Hope\\")
        print("5. Re-run this script!\n")
        sys.exit(1)

    print(f"\nFound '{creds_file.name}'. Launching browser authentication flow...")
    print("Please approve access to Gmail, Calendar, and Sheets in the browser window.\n")

    try:
        flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
        creds = flow.run_local_server(port=0)

        token_file = config.google_token_file
        token_file.write_text(creds.to_json(), encoding="utf-8")

        print("=" * 65)
        print("✅ SUCCESS! Google Workspace OAuth authorization complete!")
        print(f"Token saved to: {token_file}")
        print("Hope UltraLight can now access Gmail, Calendar, and Sheets.")
        print("=" * 65 + "\n")

    except Exception as e:
        print(f"\n❌ OAuth authorization failed: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

