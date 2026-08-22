"""
Shared yt-dlp configuration.

YouTube (2025–2026) often 403s high DASH (bestvideo+bestaudio) under SABR /
PO-token experiments, while progressive muxed formats still work.

Strategy: callers should try FORMAT_VIDEO_HQ first, then FORMAT_VIDEO_SAFE.
Clients: android+web matched successful local downloads on this project.
"""

import os
import subprocess
from pathlib import Path
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


# ---------------------------------------------------------------------------
# Shared CLI-invocation plumbing.
#
# clips.py, transcript.py, and download.py all shelled out to yt-dlp with
# their own near-identical copies of "add UA/referer/cookies/extractor-args
# flags, then run and cascade through format_attempts on a YouTube-style
# block." That logic lived in three places and drifted slightly each time.
# It now lives here once; routes only supply the parts that differ (the
# yt-dlp verbs specific to that route, e.g. --download-sections).
# ---------------------------------------------------------------------------


def base_cli_flags(url: str) -> list[str]:
    """UA / referer / cookies / extractor-args flags shared by every yt-dlp
    subprocess call. Callers append these to their route-specific flags,
    then the target URL last."""
    options = build_ydl_options(url)
    flags: list[str] = ["--user-agent", options["http_headers"]["User-Agent"]]

    referer = options["http_headers"].get("Referer")
    if referer:
        flags += ["--referer", referer]

    # Optional: export YTDLP_COOKIES=/path/to/cookies.txt for tougher sessions
    # (see docs/SESSION_NOTES.md "PO tokens / proxies").
    cookies = os.getenv("YTDLP_COOKIES", "").strip()
    if cookies and Path(cookies).is_file():
        flags += ["--cookies", cookies]

    clients = options.get("extractor_args", {}).get("youtube", {}).get("player_client", [])
    if clients:
        flags += ["--extractor-args", f"youtube:player_client={','.join(clients)}"]

    return flags


def looks_like_youtube_block(stderr: str) -> bool:
    """True if stderr matches the SABR/PO-token/DRM-style failures documented
    in docs/SESSION_NOTES.md (Test log T2/T3/T5) that warrant cascading to
    the next, safer format rather than failing outright."""
    s = (stderr or "").lower()
    return any(
        token in s
        for token in ("403", "forbidden", "sabr", "po token", "drm protected", "http error 403")
    )


def run_with_format_cascade(
    build_cmd,
    url: str,
    work_dir: Path,
    output_id: str,
    want_audio_only: bool = False,
    timeout: int = 300,
) -> tuple[subprocess.CompletedProcess, str]:
    """Run yt-dlp, trying format_attempts(url) in order.

    `build_cmd(fmt)` must return the full argv list for that format attempt
    (route-specific flags + base_cli_flags(url) + [url]).

    On a YouTube-style block (see looks_like_youtube_block), partial output
    for this attempt is cleared and the next, safer format is tried -- this
    is the HQ-DASH-then-progressive cascade from docs/SESSION_NOTES.md.
    Any other kind of failure raises immediately without cascading.

    Returns (CompletedProcess, format_used) on success. Raises RuntimeError
    with the last stderr/stdout on exhausting all attempts.
    """
    attempts = format_attempts(url, want_audio_only=want_audio_only)
    last_err = "unknown yt-dlp error"

    for i, fmt in enumerate(attempts):
        result = subprocess.run(build_cmd(fmt), capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            return result, fmt

        last_err = result.stderr or result.stdout or last_err
        is_last_attempt = i + 1 == len(attempts)
        if not is_last_attempt and looks_like_youtube_block(last_err):
            for p in work_dir.glob(f"{output_id}*"):
                p.unlink(missing_ok=True)
            continue
        raise RuntimeError(last_err)

    raise RuntimeError(last_err)
