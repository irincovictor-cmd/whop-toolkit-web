"""
POST /clips/extract

Cut a timestamped clip from any yt-dlp-supported URL.

YouTube quality cascade (see docs/SESSION_NOTES.md for the CLI tests this
is based on):
  1) Try high DASH (up to 1080p) -- same class of quality the old CLI often got
  2) On 403 / SABR-style failure, retry progressive-safe formats

The cascade + shared CLI-flag logic lives in app.core.ytdlp_client so
clips.py, transcript.py, and download.py don't each carry their own copy.
"""

import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from app.core.local_output import save_to_local_output
from app.core.ytdlp_client import base_cli_flags, probe_video_quality, run_with_format_cascade

router = APIRouter()

MAX_CLIP_SECONDS = 600


class ClipRequest(BaseModel):
    url: str
    start: float = Field(..., ge=0)
    end: float = Field(..., gt=0)
    format: str = Field(default="mp4", pattern="^(mp4|mp3|wav)$")


def _seconds_to_timestamp(s: float) -> str:
    h, rem = divmod(int(s), 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02}:{m:02}:{sec:02}"


def _cleanup(work_dir: Path) -> None:
    shutil.rmtree(work_dir, ignore_errors=True)


@router.post("/extract")
def extract_clip(req: ClipRequest):
    if req.end <= req.start:
        raise HTTPException(status_code=400, detail="end must be after start")
    if req.end - req.start > MAX_CLIP_SECONDS:
        raise HTTPException(status_code=400, detail=f"Clips are capped at {MAX_CLIP_SECONDS}s")

    work_dir = Path(tempfile.mkdtemp(prefix="clip_"))
    output_id = uuid.uuid4().hex[:10]
    output_template = str(work_dir / f"{output_id}.%(ext)s")
    section = f"*{_seconds_to_timestamp(req.start)}-{_seconds_to_timestamp(req.end)}"
    want_audio_only = req.format in ("mp3", "wav")

    def build_cmd(fmt: str) -> list[str]:
        return [
            "yt-dlp",
            "--download-sections", section,
            "--force-keyframes-at-cuts",
            "-f", fmt,
            "--merge-output-format", "mp4",
            "-o", output_template,
            *base_cli_flags(req.url),
            req.url,
        ]

    try:
        try:
            run_with_format_cascade(
                build_cmd, req.url, work_dir, output_id, want_audio_only=want_audio_only
            )
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=f"yt-dlp failed: {str(e)[-800:]}")

        downloaded = list(work_dir.glob(f"{output_id}.*"))
        if not downloaded:
            raise HTTPException(status_code=500, detail="Clip extraction produced no output file")
        source_file = downloaded[0]

        if want_audio_only:
            final_path = work_dir / f"{output_id}.{req.format}"
            codec = (
                ["-acodec", "libmp3lame", "-q:a", "2"]
                if req.format == "mp3"
                else ["-acodec", "pcm_s16le"]
            )
            convert_cmd = ["ffmpeg", "-y", "-i", str(source_file), "-vn", *codec, str(final_path)]
            conv_result = subprocess.run(convert_cmd, capture_output=True, text=True, timeout=120)
            if conv_result.returncode != 0:
                raise HTTPException(
                    status_code=500, detail=f"ffmpeg conversion failed: {conv_result.stderr[-800:]}"
                )
        else:
            final_path = source_file

        ext = req.format if want_audio_only else (final_path.suffix.lstrip(".") or "mp4")
        quality_label = None if want_audio_only else probe_video_quality(final_path)
        quality_tag = f" ({quality_label})" if quality_label else ""
        nice_name = (
            f"clip_{_seconds_to_timestamp(req.start).replace(':', '-')}"
            f"_to_{_seconds_to_timestamp(req.end).replace(':', '-')}{quality_tag}_{output_id}.{ext}"
        )
        saved = save_to_local_output(final_path, preferred_name=nice_name)
        download_name = saved.name if saved else nice_name

        return FileResponse(
            path=str(final_path),
            filename=download_name,
            media_type="application/octet-stream",
            background=BackgroundTask(_cleanup, work_dir),
            headers={"X-Video-Quality": quality_label or ""},
        )
    except HTTPException:
        _cleanup(work_dir)
        raise
