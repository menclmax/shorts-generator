# Shorts Generator (Automated)

Generates YouTube Shorts from Slovak political interview videos when you upload them to a Google Drive folder.

## Flow

1. Upload a video to your watched Drive folder
2. Original is moved to `original files/`
3. Short is generated (transcribe → find hook → trim, 9:16, subtitles)
4. Short is uploaded to a folder named after the video

## Setup

### 1. Google Drive

- Create a folder in Drive (e.g. "Shorts Input")
- Create a [Service Account](https://console.cloud.google.com/iam-admin/serviceaccounts)
- Enable the Drive API
- Download the JSON key → save as `google-credentials.json` in this directory
- Share the folder with the service account email (Editor access)
- Copy the folder ID from the URL: `drive.google.com/drive/folders/FOLDER_ID`

### 2. Supabase

- Create a project at [supabase.com](https://supabase.com)
- In Supabase Dashboard → SQL Editor, run the contents of `supabase/migrations/001_create_jobs.sql`

### 3. Environment

Copy `.env.example` to `.env` and fill in:

```
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
GOOGLE_APPLICATION_CREDENTIALS=./google-credentials.json
WATCHED_FOLDER_ID=your_folder_id
WEBHOOK_BASE_URL=https://your-deployed-url.railway.app
```

### 4. Install

```bash
python -m venv venv
source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

Requires **FFmpeg** installed (`brew install ffmpeg` on macOS).

## Run Locally

```bash
uvicorn src.app:app --reload
```

- Worker runs in the background
- POST `http://localhost:8000/sync` to manually trigger a folder scan and enqueue new videos
- Or use the Drive webhook once deployed (see below)

## Deploy (Railway)

1. Create a Railway project
2. Add environment variables
3. Set start command: `uvicorn src.app:app --host 0.0.0.0 --port $PORT`
4. Add `google-credentials.json` as a secret or env var (base64-encoded)
5. Deploy

After deploy, set `WEBHOOK_BASE_URL` to your Railway URL.

## Drive Push Notifications (Optional)

To get automatic triggers when files are added (instead of calling `/sync`):

```bash
python -m src.setup_watch
```

This registers your webhook with Drive. Note: the channel expires in ~7 days; re-run to renew.

## Manual Job Entry

You can also insert jobs directly in Supabase:

```sql
insert into jobs (drive_file_id, drive_file_name, status)
values ('DRIVE_FILE_ID', 'video.mp4', 'pending');
```
