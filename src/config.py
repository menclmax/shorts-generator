import os
import tempfile
from pathlib import Path

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# Support GOOGLE_CREDENTIALS_JSON env var (paste JSON) for Railway/cloud
_json = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")
if _json:
    try:
        _f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        _f.write(_json)
        _f.close()
        GOOGLE_CREDENTIALS_PATH = Path(_f.name)
    except Exception:
        GOOGLE_CREDENTIALS_PATH = Path("/tmp/google-credentials.json")
else:
    _path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    GOOGLE_CREDENTIALS_PATH = Path(_path) if _path else Path(__file__).parent.parent / "google-credentials.json"
WATCHED_FOLDER_ID = os.environ.get("WATCHED_FOLDER_ID", "")
WEBHOOK_BASE_URL = os.environ.get("WEBHOOK_BASE_URL", "")  # e.g. https://your-app.railway.app

WORK_DIR = Path(os.environ.get("WORK_DIR", "/tmp/shorts-generator"))
WORK_DIR.mkdir(parents=True, exist_ok=True)
