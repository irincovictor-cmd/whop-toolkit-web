"""
POST /transcript

Web successor to modules/transcript.py:get_transcript(). Preserves the same
order of operations that module always used: try platform captions first
(free, instant), fall back to local Whisper only if none exist.
"""

import subprocess
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.ytdlp_client import build_ydl_options

router = APIRouter()


class TranscriptRequest(BaseModel):
    url: str
    whisper_model: str = "base"  # base | small | medium -- same tri-tier choice the CLI offered


def _fetch_youtube_captions(video_id: str):
    """Mirrors modules/transcript.py:fetch_youtube_transcript()."""
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, CouldNotRetrieveTranscript

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
    """Mirrors modules/downloader.py:download_audio_only() -- 'ba/ba*' only,
    never pulls video, so a captionless video never risks a full download
    just to get a transcript."""
    output_id = uuid.uuid4().hex[:10]
    output_template = str(work_dir / f"{output_id}.%(ext)s")

    options = build_ydl_options(url)
    cmd = [
        "yt-dlp", "-f", "ba/ba*",
        "--extract-audio", "--audio-format", "mp3", "--audio-quality", "128K",
        "-o", output_template,
        "--user-agent", options["http_headers"]["User-Agent"],
        url,
    ]
    if "extractor_args" in options:
        cmd += ["--extractor-args", f"youtube:player_client={','.join(options['extractor_args']['youtube']['player_client'])}"]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Audio download failed: {result.stderr[-800:]}")

    files = list(work_dir.glob(f"{output_id}.*"))
    if not files:
        raise HTTPException(status_code=500, detail="Audio download produced no file")
    return files[0]


def _transcribe_with_whisper(audio_path: Path, model_size: str):
    """Mirrors modules/transcript.py:transcribe_with_whisper(), including
    the hallucination filter for repeated silence/music segments."""
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments_iter, info = model.transcribe(str(audio_path), vad_filter=True)

    segments = []
    for s in segments_iter:
        text = s.text.strip()
        if segments and segments[-1]["text"].strip().lower() == text.lower():
            segments[-1]["end"] = s.end  # collapse repeats instead of duplicating
            continue
        segments.append({"start": s.start, "end": s.end, "text": text})

    return {"source": "whisper", "language": info.language, "segments": segments}


@router.post("")
def get_transcript(req: TranscriptRequest):
    from app.routes.metadata import get_metadata
    info = get_metadata(req.url)

    if info.get("video_id") and ("youtube.com" in req.url or "youtu.be" in req.url):
        captions = _fetch_youtube_captions(info["video_id"])
        if captions:
            return captions

    work_dir = Path(tempfile.mkdtemp(prefix="transcript_"))
    try:
        audio_path = _download_audio_only(req.url, work_dir)
        return _transcribe_with_whisper(audio_path, req.whisper_model)
    finally:
        for f in work_dir.glob("*"):
            f.unlink(missing_ok=True)
