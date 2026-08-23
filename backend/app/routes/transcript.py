"""
POST /transcript

Try YouTube captions first when applicable; otherwise audio-only download +
Whisper. Works for any yt-dlp URL (TikTok/IG/etc. go straight to Whisper).
Returns timed segments suitable for SRT export on the client.

POST /transcript/local

Same Whisper path, but for a video file already sitting on the user's
device (e.g. something they downloaded earlier) instead of a URL --
mirrors the CLI tool's import_local_video() + extract_audio_from_source()
flow. No YouTube captions possible for a local file, so this always goes
straight to Whisper.
"""

import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.core.ytdlp_client import base_cli_flags, detect_platform

router = APIRouter()


class TranscriptRequest(BaseModel):
    url: str
    whisper_model: str = "base"  # base | small | medium


def _fetch_youtube_captions(video_id: str):
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import (
        TranscriptsDisabled,
        NoTranscriptFound,
        CouldNotRetrieveTranscript,
    )

    try:
        raw = YouTubeTranscriptApi().fetch(video_id)
    except (TranscriptsDisabled, NoTranscriptFound, CouldNotRetrieveTranscript):
        return None

    return {
        "source": "youtube",
        "segments": [
            {"start": line.start, "end": line.start + line.duration, "text": line.text}
            for line in raw
        ],
    }


def _download_audio_only(url: str, work_dir: Path) -> Path:
    output_id = uuid.uuid4().hex[:10]
    output_template = str(work_dir / f"{output_id}.%(ext)s")

    cmd = [
        "yt-dlp",
        "-f", "ba/ba*/bestaudio/best",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "128K",
        "-o", output_template,
        *base_cli_flags(url),
        url,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"Audio download failed: {(result.stderr or result.stdout)[-800:]}",
        )

    files = list(work_dir.glob(f"{output_id}.*"))
    if not files:
        raise HTTPException(status_code=500, detail="Audio download produced no file")
    return files[0]


def _transcribe_with_whisper(audio_path: Path, model_size: str):
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments_iter, info = model.transcribe(str(audio_path), vad_filter=True)

    segments = []
    for s in segments_iter:
        text = s.text.strip()
        if segments and segments[-1]["text"].strip().lower() == text.lower():
            segments[-1]["end"] = s.end
            continue
        segments.append({"start": s.start, "end": s.end, "text": text})

    return {"source": "whisper", "language": info.language, "segments": segments}


def _extract_audio_from_upload(video_path: Path, work_dir: Path) -> Path:
    """ffmpeg audio-extract for an already-uploaded local file -- mirrors
    the CLI's extract_audio_from_source()."""
    audio_path = work_dir / "audio.mp3"
    conv = subprocess.run(
        ["ffmpeg", "-y", "-i", str(video_path), "-vn", "-acodec", "libmp3lame", "-q:a", "2", str(audio_path)],
        capture_output=True, text=True, timeout=600,
    )
    if conv.returncode != 0 or not audio_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Couldn't extract audio from that file: {conv.stderr[-800:]}",
        )
    return audio_path


@router.post("")
def get_transcript(req: TranscriptRequest):
    from app.routes.metadata import get_metadata

    platform = detect_platform(req.url)
    info = get_metadata(req.url)

    # YouTube: free captions when available
    if platform == "youtube" and info.get("video_id"):
        captions = _fetch_youtube_captions(info["video_id"])
        if captions:
            captions["platform"] = platform
            captions["title"] = info.get("title")
            return captions

    # All platforms (and YouTube without captions): Whisper on audio-only
    work_dir = Path(tempfile.mkdtemp(prefix="transcript_"))
    try:
        audio_path = _download_audio_only(req.url, work_dir)
        result = _transcribe_with_whisper(audio_path, req.whisper_model)
        result["platform"] = platform
        result["title"] = info.get("title")
        return result
    finally:
        for f in work_dir.glob("*"):
            f.unlink(missing_ok=True)


# 500 MB cap -- generous for a downloaded clip/short video, but stops an
# accidental multi-GB upload from tying up the server. Adjust if this
# turns out too tight for real usage.
MAX_UPLOAD_BYTES = 500 * 1024 * 1024


@router.post("/local")
async def get_transcript_from_upload(
    file: UploadFile = File(...),
    whisper_model: str = Form("base"),
):
    work_dir = Path(tempfile.mkdtemp(prefix="transcript_local_"))
    try:
        suffix = Path(file.filename or "upload").suffix or ".mp4"
        upload_path = work_dir / f"upload{suffix}"

        size = 0
        with open(upload_path, "wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large -- {MAX_UPLOAD_BYTES // (1024 * 1024)}MB max.",
                    )
                out.write(chunk)

        audio_path = _extract_audio_from_upload(upload_path, work_dir)
        result = _transcribe_with_whisper(audio_path, whisper_model)
        result["platform"] = "local"
        result["title"] = file.filename
        return result
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
