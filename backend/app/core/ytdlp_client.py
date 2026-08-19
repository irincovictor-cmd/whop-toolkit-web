"""
Shared yt-dlp configuration.

YouTube SABR experiments often 403 high-quality DASH (bestvideo+bestaudio)
while progressive formats (e.g. format 18) still work with android+web.
Validated locally 2026-08: android,web + progressive/fallback succeeded
where default/android + 401+251 failed mid-download with 403.
"""

from urllib.parse import urlparse

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# Prefer android+web: avoids ANDROID_VR defaults and matched a successful
# full download when mweb/tv reported DRM-only / missing formats.
YOUTUBE_PLAYER_CLIENTS = ["android", "web"]

# Prefer a single progressive stream when possible (SABR-safe), then DASH.
YOUTUBE_FORMAT_VIDEO = (
    "best[height<=1080][protocol^=http]/best[height<=720]/"
    "bestvideo[height<=1080]+bestaudio/best"
)
YOUTUBE_FORMAT_AUDIO = "bestaudio/best"


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


def format_selector(url: str, want_audio_only: bool = False) -> str:
    if want_audio_only:
        return YOUTUBE_FORMAT_AUDIO if detect_platform(url) == "youtube" else "bestaudio/best"
    if detect_platform(url) == "youtube":
        return YOUTUBE_FORMAT_VIDEO
    return "bestvideo[height<=1080]+bestaudio/best"
