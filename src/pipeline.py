"""Transcribe, analyze, and generate short."""

import subprocess
from pathlib import Path

from openai import OpenAI


def _client():
    return OpenAI()


def transcribe(audio_path: Path) -> list[dict]:
    """Transcribe with Whisper. Returns segments [{start, end, text}]."""
    with open(audio_path, "rb") as f:
        t = _client().audio.transcriptions.create(
            file=f,
            model="whisper-1",
            language="sk",
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )
    segs = getattr(t, "segments", None) or []
    return [{"start": s["start"], "end": s["end"], "text": s.get("text", "")} for s in segs]


def analyze_hooks(segments: list[dict]) -> list[dict]:
    """Use GPT to find best hook moments. Returns [{start, end, reason}]."""
    lines = [f"[{int(s['start'])}s] {s['text']}" for s in segments]
    transcript = "\n".join(lines)
    r = _client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You analyze Slovak political interview transcripts. Find the most viral, hook-worthy moments for YouTube Shorts. Return a JSON array of clips: [{start, end, reason}]. start/end in seconds. Pick 1-3 clips, 15-60 sec each.",
            },
            {
                "role": "user",
                "content": f"Analyze:\n\n{transcript}",
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
    )
    import json
    data = json.loads(r.choices[0].message.content or "{}")
    clips = data.get("clips", data.get("suggestions", []))
    if isinstance(clips, dict):
        clips = [clips]
    return [c for c in clips if isinstance(c.get("start"), (int, float)) and isinstance(c.get("end"), (int, float))]


def segments_to_srt(segments: list[dict], clip_start: float, clip_end: float) -> str:
    out = []
    for i, s in enumerate(segments):
        if s["end"] <= clip_start or s["start"] >= clip_end:
            continue
        start = max(0, s["start"] - clip_start)
        end = min(clip_end - clip_start, s["end"] - clip_start)
        out.append(f"{i+1}\n{_srt_time(start)} --> {_srt_time(end)}\n{s['text'].strip()}\n")
    return "\n".join(out)


def _srt_time(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int((sec % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def create_short(video_path: Path, clip: dict, segments: list[dict], out_path: Path) -> Path:
    """Trim, crop 9:16, burn subtitles."""
    start = float(clip["start"])
    end = float(clip["end"])
    work_dir = video_path.parent
    srt_path = work_dir / "subtitles.srt"
    srt_content = segments_to_srt(segments, start, end)
    srt_path.write_text(srt_content, encoding="utf-8")

    filter_complex = (
        f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS,"
        f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        f"subtitles=subtitles.srt[v];"
        f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a]"
    )
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-c:a", "aac",
        "-shortest", str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, cwd=str(work_dir))
    srt_path.unlink(missing_ok=True)
    return out_path
