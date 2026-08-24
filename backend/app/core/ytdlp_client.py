"""
Shared yt-dlp configuration.

YouTube (2025–2026) often 403s high DASH (bestvideo+bestaudio) under SABR /
PO-token experiments, while progressive muxed formats still work.

Strategy: callers should try FORMAT_VIDEO_HQ first, then FORMAT_VIDEO_SAFE.
Clients: android+web matched successful local downloads on this project.

After a "successful" download we also ffprobe for an audio stream. yt-dlp can
exit 0 with video-only output when DASH merge is incomplete — that produced
silent full-video downloads while section clips (remuxed) still had sound.
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

# android,web matched progressive success in session notes; default can surface VR/SABR paths
YOUTUBE_PLAYER_CLIENTS = ["android", "web"]

# Attempt first: real 720/1080 when YouTube allows DASH + audio merge.
FORMAT_VIDEO_HQ = (
    "bestvideo[height<=1080]+bestaudio/best[height<=1080][ext=mp4]/best[height<=1080]"
)
# Fallback: progressive / SABR-safe (often muxed mp4 with audio).
FORMAT_VIDEO_SAFE = (
    "best[height<=720][ext=mp4]/best[height<=720]/best[height<=480][ext=mp4]/best"
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
    subprocess call."""
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
    """True if stderr matches SABR/PO-token/DRM-style failures that warrant cascade."""
    s = (stderr or "").lower()
    return any(
        token in s
        for token in ("403", "forbidden", "sabr", "po token", "drm protected", "http error 403")
    )


def probe_video_quality(path: Path) -> str | None:
    """Returns actual resolution e.g. '1080p' via ffprobe, or None."""
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


def probe_has_audio(path: Path) -> bool:
    """True if ffprobe finds at least one audio stream."""
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "a",
        "-show_entries", "stream=codec_type",
        "-of", "csv=p=0", str(path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            return False
        return "audio" in (result.stdout or "").lower()
    except Exception:
        return False


def _first_output_file(work_dir: Path, output_id: str) -> Path | None:
    matches = sorted(work_dir.glob(f"{output_id}.*"))
    return matches[0] if matches else None


def run_with_format_cascade(
    build_cmd,
    url: str,
    work_dir: Path,
    output_id: str,
    want_audio_only: bool = False,
    timeout: int = 600,
) -> tuple[subprocess.CompletedProcess, str]:
    """Run yt-dlp, trying format_attempts(url) in order.

    On YouTube-style block (403/SABR), clear partials and try the next format.
    On exit 0 with a video file that has **no audio** (and caller wanted video),
    treat as failure and cascade — fixes silent full-video downloads.

    Returns (CompletedProcess, format_used) on success.
    """
    attempts = format_attempts(url, want_audio_only=want_audio_only)
    last_err = "unknown yt-dlp error"

    for i, fmt in enumerate(attempts):
        result = subprocess.run(build_cmd(fmt), capture_output=True, text=True, timeout=timeout)
        is_last_attempt = i + 1 == len(attempts)

        if result.returncode == 0:
            out = _first_output_file(work_dir, output_id)
            if want_audio_only or out is None:
                return result, fmt
            if probe_has_audio(out):
                return result, fmt

            last_err = (
                f"download produced a file without audio (format={fmt}); "
                "retrying safer format"
            )
            for p in work_dir.glob(f"{output_id}*"):
                p.unlink(missing_ok=True)
            if is_last_attempt:
                raise RuntimeError(
                    last_err + " — all format attempts lacked an audio track"
                )
            continue

        last_err = result.stderr or result.stdout or last_err
        if not is_last_attempt and looks_like_youtube_block(last_err):
            for p in work_dir.glob(f"{output_id}*"):
                p.unlink(missing_ok=True)
            continue
        raise RuntimeError(last_err)

    raise RuntimeError(last_err)
