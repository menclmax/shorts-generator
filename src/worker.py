"""Process jobs from Supabase queue."""

import subprocess
import time
from pathlib import Path

from supabase import create_client

from src.config import (
    GOOGLE_CREDENTIALS_PATH,
    OPENAI_API_KEY,
    SUPABASE_SERVICE_KEY,
    SUPABASE_URL,
    WATCHED_FOLDER_ID,
    WORK_DIR,
)
from src.drive import (
    download_file,
    ensure_folder,
    get_drive_service,
    move_file,
    sanitize_folder_name,
    upload_file,
)
from src.pipeline import analyze_hooks, create_short, transcribe


def extract_audio(video_path: Path) -> Path:
    """Extract audio for Whisper."""
    audio_path = video_path.with_suffix(".m4a")
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(video_path),
            "-vn", "-c:a", "aac", "-b:a", "128k",
            str(audio_path),
        ],
        check=True,
        capture_output=True,
    )
    return audio_path


def process_job(job_id: str, drive_file_id: str, drive_file_name: str) -> None:
    """Download, process, move original, upload short."""
    work = WORK_DIR / job_id
    work.mkdir(parents=True, exist_ok=True)
    video_path = work / (drive_file_name or "video.mp4")

    try:
        service = get_drive_service(Path(GOOGLE_CREDENTIALS_PATH))
        download_file(service, drive_file_id, video_path)

        audio_path = extract_audio(video_path)
        segments = transcribe(audio_path)
        audio_path.unlink(missing_ok=True)

        if not segments:
            raise ValueError("No speech detected in video")

        clips = analyze_hooks(segments)
        if not clips:
            raise ValueError("No hook moments found")

        clip = clips[0]
        short_path = work / "short.mp4"
        create_short(video_path, clip, segments, short_path)

        original_folder_id = ensure_folder(service, WATCHED_FOLDER_ID, "original files")
        move_file(service, drive_file_id, original_folder_id)

        base_name = sanitize_folder_name(drive_file_name or "video")
        output_folder_id = ensure_folder(service, WATCHED_FOLDER_ID, base_name)
        upload_file(service, short_path, output_folder_id, f"{base_name}_short.mp4")

    finally:
        for f in work.iterdir():
            f.unlink(missing_ok=True)
        work.rmdir()


def run_worker():
    """Poll Supabase and process pending jobs."""
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    while True:
        try:
            r = (
                supabase.table("jobs")
                .select("id, drive_file_id, drive_file_name")
                .eq("status", "pending")
                .limit(1)
                .execute()
            )
            rows = r.data or []
            if not rows:
                time.sleep(10)
                continue

            job = rows[0]
            supabase.table("jobs").update({"status": "processing"}).eq("id", job["id"]).execute()

            try:
                process_job(
                    job["id"],
                    job["drive_file_id"],
                    job.get("drive_file_name"),
                )
                supabase.table("jobs").update({"status": "completed"}).eq("id", job["id"]).execute()
            except Exception as e:
                supabase.table("jobs").update(
                    {"status": "failed", "error": str(e)}
                ).eq("id", job["id"]).execute()

        except Exception as e:
            print(f"Worker error: {e}")
            time.sleep(30)


if __name__ == "__main__":
    run_worker()
