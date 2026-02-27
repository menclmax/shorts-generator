"""Register Drive push notifications for the watched folder."""

import sys
from pathlib import Path

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from src.config import GOOGLE_CREDENTIALS_PATH, WATCHED_FOLDER_ID, WEBHOOK_BASE_URL

SCOPES = ["https://www.googleapis.com/auth/drive"]
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"


def setup_watch():
    if not WEBHOOK_BASE_URL or not WATCHED_FOLDER_ID:
        print("Set WEBHOOK_BASE_URL and WATCHED_FOLDER_ID in env")
        sys.exit(1)

    creds = Credentials.from_service_account_file(
        str(Path(GOOGLE_CREDENTIALS_PATH)), scopes=[DRIVE_SCOPE]
    )
    service = build("drive", "v3", credentials=creds)

    body = {
        "id": "shorts-generator-watch",
        "type": "web_hook",
        "address": f"{WEBHOOK_BASE_URL.rstrip('/')}/webhook/drive",
    }
    request = service.files().watch(fileId=WATCHED_FOLDER_ID, body=body)
    r = request.execute()
    print("Watch registered:")
    print(f"  Channel ID: {r.get('id')}")
    print(f"  Expires: {r.get('expiration')}")
    print("Note: Channel expires in ~7 days. Re-run this script to renew.")


if __name__ == "__main__":
    setup_watch()
