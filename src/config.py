import os
from pathlib import Path

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
GOOGLE_CREDENTIALS_PATH = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS",
    Path(__file__).parent.parent / "google-credentials.json",
)
WATCHED_FOLDER_ID = os.environ.get("WATCHED_FOLDER_ID", "")
WEBHOOK_BASE_URL = os.environ.get("WEBHOOK_BASE_URL", "")  # e.g. https://your-app.railway.app

WORK_DIR = Path(os.environ.get("WORK_DIR", "/tmp/shorts-generator"))
WORK_DIR.mkdir(parents=True, exist_ok=True)
