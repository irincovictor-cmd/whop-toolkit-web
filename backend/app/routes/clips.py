"""
POST /clips/extract

Web successor to modules/downloader.py:stream_crop_clip(). The CLI version
resolved a raw CDN URL and fed it to ffmpeg with -ss/-to before -i. On the
web, we let yt-dlp do the range-limited fetch itself via --download-sections
instead -- more robust across the wider variety of source platforms a
public tool will actually see (TikTok/Instagram/Vimeo/etc, not just
YouTube), since yt-dlp's own section-download logic already knows how to
handle each site's quirks. Either way, the goal from the CLI carries over
unchanged: never pull the full source video for a short clip.
"""

import subprocess
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.core.ytdlp_client import build_ydl_options

router = APIRouter()

MAX_CLIP_SECONDS = 600  # sanity cap; adjust per your product's actual limits


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

    # yt-dlp's own section-download feature -- this is what avoids
    # downloading the full source video, the same goal the CLI's dual
    # -ss/-to-before-input ffmpeg trick served, just via yt-dlp's native
    # mechanism instead of resolving raw stream URLs ourselves.
    cmd = [
        "yt-dlp",
        "--download-sections", section,
        "--force-keyframes-at-cuts",
        "-f", "bestvideo[height<=1080]+bestaudio/best" if req.format == "mp4" else "bestaudio",
        "--merge-output-format", "mp4",
        "-o", output_template,
        req.url,
    ]

    options = build_ydl_options(req.url)
    if "extractor_args" in options:
        for client in options["extractor_args"].get("youtube", {}).get("player_client", []):
            pass  # translated into --extractor-args below
        import json
        cmd += ["--extractor-args", f"youtube:player_client={','.join(options['extractor_args']['youtube']['player_client'])}"]
    cmd += ["--user-agent", options["http_headers"]["User-Agent"]]
    if options["http_headers"].get("Referer"):
        cmd += ["--referer", options["http_headers"]["Referer"]]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"yt-dlp failed: {result.stderr[-800:]}")

    downloaded = list(work_dir.glob(f"{output_id}.*"))
    if not downloaded:
        raise HTTPException(status_code=500, detail="Clip extraction produced no output file")
    source_file = downloaded[0]

    # Format conversion (mp3/wav extraction) -- same ffmpeg recipes as the
    # CLI's modules/converter.py, unchanged, since those were already correct.
    if req.format in ("mp3", "wav"):
        final_path = work_dir / f"{output_id}.{req.format}"
        codec = ["-acodec", "libmp3lame", "-q:a", "2"] if req.format == "mp3" else ["-acodec", "pcm_s16le"]
        convert_cmd = ["ffmpeg", "-y", "-i", str(source_file), "-vn", *codec, str(final_path)]
        conv_result = subprocess.run(convert_cmd, capture_output=True, text=True, timeout=120)
        if conv_result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"ffmpeg conversion failed: {conv_result.stderr[-800:]}")
    else:
        final_path = source_file

    # In production, upload final_path to S3-compatible object storage here
    # and return a signed URL instead of streaming the file through the
    # API process -- FileResponse below is the simple/local-dev path.
    return FileResponse(
        path=str(final_path),
        filename=final_path.name,
        media_type="application/octet-stream",
    )
