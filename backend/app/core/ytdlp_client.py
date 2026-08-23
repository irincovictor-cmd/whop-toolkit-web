"""
Shared yt-dlp configuration.

YouTube (2025–2026) often 403s high DASH (bestvideo+bestaudio) under SABR /
PO-token experiments, while progressive muxed formats still work.

Strategy: callers should try FORMAT_VIDEO_HQ first, then FORMAT_VIDEO_SAFE.
Clients: android+web matched successful local downloads on this project.
"""

import json
import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

YOUTUBE_PLAYER_CLIENTS = ["default", "android"]

# Attempt first: real 720/1080 when YouTube allows DASH.
# NOTE: deliberately NOT falling through to an unrestricted "/best" here.
# yt-dlp evaluates format selectors internally -- an unbounded trailing
# fallback lets it silently pick any available format (even very low res)
# while still exiting 0, which meant our own cascade below never even
# triggered because it only sees the low quality as a "success." Keeping
# both alternatives height-capped forces a real failure when 1080 truly
# isn't available, so run_with_format_cascade() actually gets a chance to
# retry with FORMAT_VIDEO_SAFE instead of yt-dlp quietly downgrading first.
# Confirmed via side-by-side comparison against the CLI tool, which never
# had this trailing fallback and consistently got higher quality.
FORMAT_VIDEO_HQ = "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
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


def base_cli_flags(url: str) -> list[str]:
    """UA / referer / cookies / extractor-args flags shared by every yt-dlp
    subprocess call. Callers append these to their route-specific flags,
    then the target URL last."""
    options = build_ydl_options(url)
    flags: list[str] = ["--user-agent", options["http_headers"]["User-Agent"]]

    referer = options["http_headers"].get("Referer")
    if referer:
        flags += ["--referer", referer]

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


def probe_video_quality(path: Path) -> str | None:
    """Returns the actual achieved resolution as e.g. '1080p', by reading
    the real video stream height with ffprobe -- not what we *asked*
    yt-dlp for, what it actually delivered. This is what lets a filename
    honestly say "(720p)" when the safe-format cascade fired, instead of
    the user only finding out by eyeballing playback quality. Returns None
    for audio-only files (no video stream) or if ffprobe fails."""
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=height",
        "-of", "json", str(path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        if not streams or not streams[0].get("height"):
            return None
        return f"{streams[0]['height']}p"
    except Exception:
        return None


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
