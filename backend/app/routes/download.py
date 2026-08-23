"""
POST /download

Full-video download for any yt-dlp-supported platform (YouTube, TikTok,
Instagram, X/Twitter, Facebook, Vimeo, generic sites). This is the
"grab the whole video" counterpart to /clips/extract's "grab a timestamped
section" -- same HQ-then-safe format cascade, just without
--download-sections since the whole file is wanted.

Product framing (see docs/SESSION_NOTES.md "What done looks like"): this is
a pass-through fetch-and-hand-to-the-user, not permanent hosting. Files are
streamed back and the temp dir is removed once the response finishes.
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
from app.core.ytdlp_client import (
    base_cli_flags,
    detect_platform,
    probe_video_quality,
    run_with_format_cascade,
)

router = APIRouter()

SUPPORTED_PLATFORMS = {
    "youtube",
    "tiktok",
    "instagram",
    "twitter",
    "facebook",
    "vimeo",
}


class DownloadRequest(BaseModel):
    url: str
    format: str = Field(default="mp4", pattern="^(mp4|mp3|wav)$")


def _cleanup(work_dir: Path) -> None:
    shutil.rmtree(work_dir, ignore_errors=True)


@router.post("")
def download_video(req: DownloadRequest):
    platform = detect_platform(req.url)
    work_dir = Path(tempfile.mkdtemp(prefix="download_"))
    output_id = uuid.uuid4().hex[:10]
    output_template = str(work_dir / f"{output_id}.%(ext)s")
    want_audio_only = req.format in ("mp3", "wav")

    def build_cmd(fmt: str) -> list[str]:
        return [
            "yt-dlp",
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
            msg = str(e)
            hint = ""
            low = msg.lower()
            if "login" in low or "private" in low:
                hint = " (this looks like a private/login-gated post -- set YTDLP_COOKIES.)"
            elif platform not in SUPPORTED_PLATFORMS:
                hint = f" ({platform} isn't in the verified platform list yet -- yt-dlp may still support it.)"
            raise HTTPException(status_code=500, detail=f"yt-dlp failed: {msg[-800:]}{hint}")

        downloaded = list(work_dir.glob(f"{output_id}.*"))
        if not downloaded:
            raise HTTPException(status_code=500, detail="Download produced no output file")
        source_file = downloaded[0]

        if want_audio_only:
            final_path = work_dir / f"{output_id}.{req.format}"
            codec = (
                ["-acodec", "libmp3lame", "-q:a", "2"]
                if req.format == "mp3"
                else ["-acodec", "pcm_s16le"]
            )
            conv = subprocess.run(
                ["ffmpeg", "-y", "-i", str(source_file), "-vn", *codec, str(final_path)],
                capture_output=True, text=True, timeout=180,
            )
            if conv.returncode != 0:
                raise HTTPException(
                    status_code=500, detail=f"ffmpeg conversion failed: {conv.stderr[-800:]}"
                )
        else:
            final_path = source_file

        ext = req.format if want_audio_only else (final_path.suffix.lstrip(".") or "mp4")
        quality_label = None if want_audio_only else probe_video_quality(final_path)
        quality_tag = f" ({quality_label})" if quality_label else ""
        nice_name = f"{platform}{quality_tag}_{output_id}.{ext}"
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
