"""
POST /clips/extract

Uses yt-dlp --download-sections for range fetches. YouTube format/clients
come from app.core.ytdlp_client (android+web, progressive-first) after
SABR 403 issues with bestvideo+bestaudio only.
"""

import subprocess
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.core.local_output import save_to_local_output
from app.core.ytdlp_client import build_ydl_options, format_selector

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
    fmt = format_selector(req.url, want_audio_only=(req.format != "mp4"))
    options = build_ydl_options(req.url)

    # URL must be last. Options after the URL are easy to get wrong.
    cmd = [
        "yt-dlp",
        "--download-sections", section,
        "--force-keyframes-at-cuts",
        "-f", fmt,
        "--merge-output-format", "mp4",
        "-o", output_template,
        "--user-agent", options["http_headers"]["User-Agent"],
    ]
    if options["http_headers"].get("Referer"):
        cmd += ["--referer", options["http_headers"]["Referer"]]
    if "extractor_args" in options:
        clients = options["extractor_args"].get("youtube", {}).get("player_client", [])
        if clients:
            cmd += [
                "--extractor-args",
                f"youtube:player_client={','.join(clients)}",
            ]
    cmd.append(req.url)

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"yt-dlp failed: {result.stderr[-800:]}")

    downloaded = list(work_dir.glob(f"{output_id}.*"))
    if not downloaded:
        raise HTTPException(status_code=500, detail="Clip extraction produced no output file")
    source_file = downloaded[0]

    if req.format in ("mp3", "wav"):
        final_path = work_dir / f"{output_id}.{req.format}"
        codec = ["-acodec", "libmp3lame", "-q:a", "2"] if req.format == "mp3" else ["-acodec", "pcm_s16le"]
        convert_cmd = ["ffmpeg", "-y", "-i", str(source_file), "-vn", *codec, str(final_path)]
        conv_result = subprocess.run(convert_cmd, capture_output=True, text=True, timeout=120)
        if conv_result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"ffmpeg conversion failed: {conv_result.stderr[-800:]}")
    else:
        final_path = source_file

    nice_name = (
        f"clip_{_seconds_to_timestamp(req.start).replace(':', '-')}"
        f"_to_{_seconds_to_timestamp(req.end).replace(':', '-')}"
        f"_{output_id}.{req.format if req.format in ('mp3', 'wav') else final_path.suffix.lstrip('.') or 'mp4'}"
    )
    saved = save_to_local_output(final_path, preferred_name=nice_name)
    download_name = saved.name if saved else nice_name

    return FileResponse(
        path=str(final_path),
        filename=download_name,
        media_type="application/octet-stream",
    )
