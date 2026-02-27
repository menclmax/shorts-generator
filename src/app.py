"""FastAPI app: webhook + Drive watch setup."""

import json
import threading
from pathlib import Path

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from supabase import create_client

from src.config import (
    GOOGLE_CREDENTIALS_PATH,
    SUPABASE_SERVICE_KEY,
    SUPABASE_URL,
    WATCHED_FOLDER_ID,
    WEBHOOK_BASE_URL,
)
from src.drive import get_drive_service, list_new_videos
from src.worker import run_worker

app = FastAPI()
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def _get_existing_file_ids() -> set[str]:
    r = supabase.table("jobs").select("drive_file_id").execute()
    return {row["drive_file_id"] for row in (r.data or [])}


@app.post("/webhook/drive")
async def drive_webhook(request: Request, background_tasks: BackgroundTasks):
    """Receive Google Drive push notifications."""
    try:
        channel_id = request.headers.get("x-goog-channel-id")
        resource_state = request.headers.get("x-goog-resource-state")
        if resource_state != "update" and resource_state != "add":
            return JSONResponse(content={"ok": True}, status_code=200)

        if not WATCHED_FOLDER_ID:
            return JSONResponse(content={"ok": True}, status_code=200)

        service = get_drive_service(Path(GOOGLE_CREDENTIALS_PATH))
        files = list_new_videos(service, WATCHED_FOLDER_ID)
        existing = _get_existing_file_ids()

        for f in files:
            if f["id"] in existing:
                continue
            mime = f.get("mimeType", "")
            if "video" not in mime and mime not in (
                "video/mp4",
                "video/webm",
                "video/quicktime",
            ):
                if not any(x in mime for x in ["video", "mp4", "webm", "quicktime"]):
                    continue
            try:
                supabase.table("jobs").insert({
                    "drive_file_id": f["id"],
                    "drive_file_name": f.get("name"),
                    "status": "pending",
                }).execute()
            except Exception:
                pass

        return JSONResponse(content={"ok": True}, status_code=200)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/sync")
async def sync_folder():
    """Manually sync the watched folder - list new videos and enqueue jobs."""
    if not WATCHED_FOLDER_ID:
        return JSONResponse(content={"error": "WATCHED_FOLDER_ID not set"}, status_code=400)
    try:
        service = get_drive_service(Path(GOOGLE_CREDENTIALS_PATH))
        files = list_new_videos(service, WATCHED_FOLDER_ID)
        existing = _get_existing_file_ids()
        added = 0
        for f in files:
            if f["id"] in existing:
                continue
            mime = f.get("mimeType", "")
            if not any(x in mime.lower() for x in ["video", "mp4", "webm", "quicktime"]):
                continue
            try:
                supabase.table("jobs").insert({
                    "drive_file_id": f["id"],
                    "drive_file_name": f.get("name"),
                    "status": "pending",
                }).execute()
                added += 1
            except Exception:
                pass
        return {"ok": True, "added": added, "total": len(files)}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/health")
def health():
    return {"status": "ok"}


def start_worker():
    threading.Thread(target=run_worker, daemon=True).start()


@app.on_event("startup")
def startup():
    start_worker()

