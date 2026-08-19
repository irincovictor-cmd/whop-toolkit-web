from pathlib import Path
from urllib.parse import urlparse
import hashlib
import json
import subprocess

from yt_dlp import YoutubeDL

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def detect_platform(url: str) -> str:
    """
    Cheap domain-based routing so YouTube-specific yt-dlp settings only
    get applied to actual YouTube URLs. yt-dlp itself auto-detects the
    site for extraction regardless -- this is purely about not sending
    youtube-only tuning (player_client args) to TikTok/Instagram/Vimeo/
    etc., and about giving non-YouTube sites the generic headers they
    tend to need instead (many expect a plausible Referer).
    """
    if not url:
        return "unknown"
    host = urlparse(url).netloc.lower()
    if "youtube.com" in host or "youtu.be" in host:
        return "youtube"
    if "tiktok.com" in host:
        return "tiktok"
    if "instagram.com" in host:
        return "instagram"
    if "twitter.com" in host or "x.com" in host:
        return "twitter"
    if "vimeo.com" in host:
        return "vimeo"
    return "generic"


def build_ydl_options(url: str, **extra) -> dict:
    """
    Shared yt-dlp options builder used by every call site (metadata,
    full download, audio-only, stream URL resolution). Applies
    YouTube-specific tuning only when the URL is actually YouTube;
    every other platform gets a generic browser User-Agent and Referer
    instead, since several (TikTok included) are inconsistent without
    something resembling a real browser request.
    """
    platform = detect_platform(url)
    options = {
        "http_headers": {
            "User-Agent": BROWSER_USER_AGENT,
            "Referer": f"https://{urlparse(url).netloc}/" if url else "",
        },
    }
    if platform == "youtube":
        options["extractor_args"] = {
            "youtube": {"player_client": ["default", "android"]},
        }
    options.update(extra)
    return options


def save_metadata(project):
    pass


def fetch_metadata(url):
    """Video metadata via yt-dlp, no download. Works for YouTube and any
    other site yt-dlp supports (TikTok, Instagram, Vimeo, etc.)."""
    options = build_ydl_options(url, quiet=True, skip_download=True)

    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)

    return {
        "title": info["title"],
        "uploader": info.get("uploader") or info.get("channel") or "Unknown",
        "duration": info["duration"],
        "video_id": info["id"],
        "url": info.get("webpage_url", url),
    }


def fetch_local_metadata(file_path):
    """
    Builds the same metadata shape as fetch_metadata(), but for a video
    file already sitting on disk (no URL). Duration comes from ffprobe;
    video_id is a short hash of the file's path so re-importing the same
    file reuses the same project instead of creating a duplicate.
    """
    file_path = Path(file_path).expanduser().resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"No file found at: {file_path}")

    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json", str(file_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe couldn't read this file -- is it a valid video? ({result.stderr.strip()})")

    duration = float(json.loads(result.stdout)["format"]["duration"])

    file_hash = hashlib.sha1(str(file_path).encode("utf-8")).hexdigest()[:10]

    return {
        "title": file_path.stem,
        "uploader": "Local Upload",
        "duration": int(duration),
        "video_id": f"local_{file_hash}",
        "url": None,
        "local_path": str(file_path),
    }
