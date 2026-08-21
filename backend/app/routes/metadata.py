"""
GET /metadata?url=...

Quiet yt-dlp probe for title/duration/uploader/platform (any supported site).
"""

from fastapi import APIRouter, HTTPException, Query
from yt_dlp import YoutubeDL

from app.core.ytdlp_client import build_ydl_options, detect_platform

router = APIRouter()


@router.get("")
def get_metadata(url: str = Query(..., description="Video URL, any yt-dlp-supported platform")):
    options = build_ydl_options(url, quiet=True, skip_download=True)
    platform = detect_platform(url)

    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Couldn't fetch that video: {e}")

    return {
        "title": info.get("title"),
        "uploader": info.get("uploader") or info.get("channel") or "Unknown",
        "duration": info.get("duration"),
        "video_id": info.get("id"),
        "url": info.get("webpage_url", url),
        "thumbnail": info.get("thumbnail"),
        "platform": platform,
        "extractor": info.get("extractor_key") or info.get("extractor"),
    }
