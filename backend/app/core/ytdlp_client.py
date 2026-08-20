"""
Shared yt-dlp configuration.

YouTube (2025–2026) often 403s high DASH (bestvideo+bestaudio) under SABR /
PO-token experiments, while progressive muxed formats still work.

Strategy: callers should try FORMAT_VIDEO_HQ first, then FORMAT_VIDEO_SAFE.
Clients: android+web matched successful local downloads on this project.
"""

from urllib.parse import urlparse

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

YOUTUBE_PLAYER_CLIENTS = ["android", "web"]

# Attempt first: real 720/1080 when YouTube allows DASH.
FORMAT_VIDEO_HQ = "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
# Fallback: progressive / SABR-safe (often ~360p–720p, but completes).
FORMAT_VIDEO_SAFE = (
    "best[height<=720][ext=mp4]/best[height<=480]/best[protocol^=http]/best"
)
FORMAT_AUDIO = "bestaudio/best"


def detect_platform(url: str) -> str:
    if not url:
        return "unknown"
    host = urlparse(url).netloc.lower()
    if "youtube.com" in host or "youtu.be" in host:
        return "youtube"
    if "tiktok.com" in host:
        return "tiktok"
    if "instagram.com" in host:
        return "instagram"
    if "facebook.com" in host or "fb.watch" in host:
        return "facebook"
    if "twitter.com" in host or "x.com" in host:
        return "twitter"
    if "vimeo.com" in host:
        return "vimeo"
    return "generic"


def build_ydl_options(url: str, **extra) -> dict:
    platform = detect_platform(url)
    options = {
        "http_headers": {
            "User-Agent": BROWSER_USER_AGENT,
            "Referer": f"https://{urlparse(url).netloc}/" if url else "",
            "Accept-Language": "en-US,en;q=0.9",
        },
    }
    if platform == "youtube":
        options["extractor_args"] = {
            "youtube": {"player_client": list(YOUTUBE_PLAYER_CLIENTS)},
        }
    options.update(extra)
    return options


def format_attempts(url: str, want_audio_only: bool = False) -> list[str]:
    """Ordered format strings to try until one succeeds."""
    if want_audio_only:
        return [FORMAT_AUDIO]
    if detect_platform(url) == "youtube":
        return [FORMAT_VIDEO_HQ, FORMAT_VIDEO_SAFE]
    return ["bestvideo[height<=1080]+bestaudio/best", "best"]


def format_selector(url: str, want_audio_only: bool = False) -> str:
    """Single format string (first preference). Prefer format_attempts for resilience."""
    return format_attempts(url, want_audio_only)[0]
