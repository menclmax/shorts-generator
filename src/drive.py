"""Google Drive API client."""

import io
import re
from pathlib import Path

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive"]

ORIGINAL_FILES_FOLDER = "original files"


def get_drive_service(credentials_path: Path):
    creds = Credentials.from_service_account_file(str(credentials_path), scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def ensure_folder(service, parent_id: str, name: str) -> str:
    """Get or create a folder. Returns folder ID."""
    q = f"'{parent_id}' in parents and name = '{name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    r = service.files().list(q=q, fields="files(id)").execute()
    files = r.get("files", [])
    if files:
        return files[0]["id"]
    f = service.files().create(
        body={"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]}
    ).execute()
    return f["id"]


def download_file(service, file_id: str, out_path: Path) -> Path:
    """Download a Drive file to disk."""
    request = service.files().get_media(fileId=file_id)
    with open(out_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
    return out_path


def move_file(service, file_id: str, new_parent_id: str) -> dict:
    """Move file to a new parent folder."""
    f = service.files().get(fileId=file_id, fields="parents").execute()
    prev = f.get("parents", [])
    return service.files().update(
        fileId=file_id,
        addParents=new_parent_id,
        removeParents=prev[0] if prev else None,
    ).execute()


def upload_file(service, path: Path, parent_id: str, name: str) -> dict:
    """Upload a file to Drive."""
    from googleapiclient.http import MediaFileUpload

    mime = "video/mp4" if path.suffix.lower() == ".mp4" else "application/octet-stream"
    media = MediaFileUpload(str(path), mimetype=mime, resumable=True)
    f = service.files().create(
        body={"name": name, "parents": [parent_id]},
        media_body=media,
        fields="id",
    ).execute()
    return f


def sanitize_folder_name(name: str) -> str:
    """Make a safe folder name from a file name."""
    base = Path(name).stem
    base = re.sub(r"[^\w\s-]", "", base)[:80].strip()
    return base or "unnamed"


def list_new_videos(service, folder_id: str) -> list[dict]:
    """List video files in folder (not in subfolders)."""
    q = f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder' and trashed = false"
    r = service.files().list(q=q, fields="files(id,name,mimeType,createdTime)").execute()
    return r.get("files", [])
