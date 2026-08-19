"""
Shared yt-dlp configuration, ported from the CLI's modules/metadata.py.

The CLI's build_ydl_options() / detect_platform() pattern is preserved
as-is here -- it was already correct: YouTube-specific tuning only applies
to YouTube URLs, every other platform gets generic browser-like headers.
That reasoning doesn't change just because this runs in a container instead
of on someone's laptop.
"""

from urllib.parse import urlparse

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


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
        },
    }
    if platform == "youtube":
        options["extractor_args"] = {
            "youtube": {"player_client": ["default", "android"]},
        }
    options.update(extra)
    return options
