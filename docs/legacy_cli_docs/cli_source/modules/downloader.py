"""
Everything that touches yt-dlp (downloading) and ffmpeg (cropping).

Two download paths:
  - download_source_video(): full video, forced to .mp4, cached in the
    project folder. Needed for the cropper.
  - download_audio_only(): small audio-only file, used only when
    Whisper fallback transcription is needed. Deleted after use by
    transcript.py.

crop_clip() does the actual cutting/resizing/aspect-ratio/bitrate work
with ffmpeg once a source video exists.
"""

import subprocess
import re
import json as _json

import config
from core.logger import get_logger
from core.project import VideoProject

log = get_logger("downloader")


# ==========================
# PROGRESS DISPLAY
# ==========================

def _render_bar(percent: float, width: int = 30) -> str:
    percent = max(0.0, min(100.0, percent))
    filled = int(width * percent / 100)
    return "#" * filled + "-" * (width - filled)


def _yt_dlp_progress_hook(d):
    """
    Passed to yt-dlp's progress_hooks. Replaces yt-dlp's own noisy
    multi-line default output with a single, clean, carriage-return
    updating status line.
    """
    if d["status"] == "downloading":
        percent_str = d.get("_percent_str", "0%").strip().replace("%", "")
        try:
            percent = float(percent_str)
        except ValueError:
            percent = 0.0
        speed = d.get("_speed_str", "?").strip()
        print(f"\rDownloading: [{_render_bar(percent)}] {percent:5.1f}%  ({speed})", end="", flush=True)
    elif d["status"] == "finished":
        print(f"\rDownloading: [{_render_bar(100)}] 100.0%  -- done, post-processing...", flush=True)


_FFMPEG_TIME_RE = re.compile(r"time=(\d+):(\d+):(\d+)\.(\d+)")


def _run_ffmpeg_with_progress(cmd: list, total_duration: float, label: str = "Processing Clip"):
    """
    Runs an ffmpeg command while rendering a single, clean, carriage-return
    updating status line based on ffmpeg's own '-stats' time= output,
    instead of blocking silently or dumping ffmpeg's raw scrolling log.
    """
    # ffmpeg's default stderr already includes progress stats; we just
    # need to read it incrementally instead of capturing it all at once.
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        universal_newlines=True, bufsize=1,
    )

    stderr_lines = []
    for line in process.stdout:
        stderr_lines.append(line)
        match = _FFMPEG_TIME_RE.search(line)
        if match and total_duration > 0:
            h, m, s, cs = match.groups()
            elapsed = int(h) * 3600 + int(m) * 60 + int(s) + int(cs) / (10 ** len(cs))
            percent = min(100.0, (elapsed / total_duration) * 100)
            print(f"\r{label}: [{_render_bar(percent)}] {percent:5.1f}%", end="", flush=True)

    process.wait()

    if process.returncode != 0:
        print(f"\r{label}: [{_render_bar(0)}]   0.0%  -- failed." + " " * 10)
        log.error(f"ffmpeg failed: {''.join(stderr_lines[-40:])}")
        return False, "".join(stderr_lines)

    print(f"\r{label}: [{_render_bar(100)}] 100.0%  -- done." + " " * 10)
    return True, "".join(stderr_lines)


# ==========================
# DOWNLOADING (yt-dlp)
# ==========================

def download_source_video(project: VideoProject, quality: str = None):
    """
    Downloads the full video, forced into .mp4 for editing-software
    compatibility. Skips the download entirely if source.mp4 already
    exists (cache check).
    """
    if project.has_source_video():
        log.info(f"Source video already cached for {project.title}")
        return project.source_video_path

    from yt_dlp import YoutubeDL
    from modules.metadata import build_ydl_options

    quality = quality or config.DEFAULT_VIDEO_QUALITY

    options = build_ydl_options(
        project.url,
        quiet=True,
        noprogress=True,
        format=f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]",
        merge_output_format="mp4",
        outtmpl=str(project.source_video_path.with_suffix("")) + ".%(ext)s",
        postprocessors=[{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4",
        }],
        progress_hooks=[_yt_dlp_progress_hook],
        # Clears yt-dlp's local cache (old nsig/player data) before each
        # download so a stale cached signature solution can't cause a
        # repeat 403. Slight cost: cache isn't reused between downloads.
        rm_cachedir=True,
    )

    print(f"Downloading source video ({quality}p, forced mp4)...")
    try:
        with YoutubeDL(options) as ydl:
            ydl.download([project.url])
        print()  # move past the progress line
    except Exception as e:
        print()
        log.error(f"Source video download failed: {e}")
        if "403" in str(e):
            print(
                "\nGot an HTTP 403 Forbidden from YouTube. This usually means yt-dlp's "
                "YouTube signature-handling is out of date -- YouTube changes this often.\n"
                'Try updating yt-dlp first:  pip install -U --pre "yt-dlp[default]"\n'
                "Then run this again."
            )
        raise RuntimeError(f"Could not download video: {e}") from e

    if not project.source_video_path.exists():
        raise RuntimeError(
            "Download finished but source.mp4 wasn't found -- check yt-dlp/ffmpeg install."
        )

    return project.source_video_path


def import_local_video(project: VideoProject, file_path):
    """
    Brings an already-owned video file into the project folder as
    source.mp4, same location the YouTube path downloads into -- so
    every downstream module (cropper, storage manager, whisper fallback)
    works identically regardless of where the video came from.

    If the file is already .mp4, it's just copied (fast, no re-encode).
    Anything else gets converted so cropping/export behaves consistently.
    """
    import shutil
    from pathlib import Path

    if project.has_source_video():
        log.info(f"Source video already imported for {project.title}")
        return project.source_video_path

    file_path = Path(file_path)
    print(f"Importing local video: {file_path.name}")

    if file_path.suffix.lower() == ".mp4":
        shutil.copy2(file_path, project.source_video_path)
    else:
        duration = _probe_duration(file_path)
        cmd = [
            "ffmpeg", "-y", "-i", str(file_path),
            "-c:v", "libx264", "-c:a", "aac",
            str(project.source_video_path),
        ]
        ok, stderr_text = _run_ffmpeg_with_progress(cmd, duration, label="Converting to mp4")
        if not ok or not project.source_video_path.exists():
            log.error(f"Local video conversion failed: {stderr_text[-1000:]}")
            raise RuntimeError("Couldn't convert that file to mp4 -- is it a valid video file?")

    return project.source_video_path


def extract_audio_from_source(project: VideoProject):
    """
    Pulls audio out of an already-imported/downloaded source.mp4 for
    Whisper. Used for local uploads, where there's no YouTube URL to
    grab audio-only from directly.
    """
    if not project.has_source_video():
        raise RuntimeError("No source video found to extract audio from.")

    duration = _probe_duration(project.source_video_path)
    cmd = [
        "ffmpeg", "-y", "-i", str(project.source_video_path),
        "-vn", "-acodec", "libmp3lame", "-q:a", "2",
        str(project.source_audio_path),
    ]
    ok, stderr_text = _run_ffmpeg_with_progress(cmd, duration, label="Extracting Audio")
    if not ok or not project.source_audio_path.exists():
        log.error(f"Audio extraction failed: {stderr_text[-1000:]}")
        raise RuntimeError("Couldn't extract audio from the source video.")

    return project.source_audio_path


def download_audio_only(project: VideoProject):
    """
    Small audio-only download, used solely to feed Whisper when a video
    has no YouTube captions. Strictly audio-only format selection means
    a video with no captions never triggers a full multi-hundred-MB
    video download just to get a transcript -- a few MB of audio is
    enough for Whisper and finishes in seconds instead of minutes.
    """
    from yt_dlp import YoutubeDL
    from modules.metadata import build_ydl_options

    options = build_ydl_options(
        project.url,
        quiet=True,
        noprogress=True,
        # 'ba/ba*' strictly prefers a real audio-only format, falling
        # back to the best available audio-bearing format only if no
        # pure audio-only stream exists -- never pulls video.
        format="ba/ba*",
        outtmpl=str(project.source_audio_path.with_suffix("")) + ".%(ext)s",
        postprocessors=[{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "128",
        }],
        progress_hooks=[_yt_dlp_progress_hook],
    )

    print("No captions available -- downloading audio only for local transcription...")
    try:
        with YoutubeDL(options) as ydl:
            ydl.download([project.url])
        print()  # move past the progress line
    except Exception as e:
        print()
        log.error(f"Audio download failed: {e}")
        raise RuntimeError(f"Could not download audio: {e}") from e

    if not project.source_audio_path.exists():
        raise RuntimeError("Audio download finished but the expected file wasn't found.")

    return project.source_audio_path


# ==========================
# STREAM CROPPING (no full download)
# ==========================

def get_stream_urls(url: str, quality: str = None):
    """
    Resolves direct, playable stream URLs for a YouTube video without
    downloading anything -- extract_info(download=False) just asks
    YouTube which CDN URLs exist for each format.

    Returns (video_url, audio_url). audio_url is None when the chosen
    format already has audio+video combined (a "progressive" stream);
    otherwise the two are separate and both are needed for ffmpeg to
    mux them back together while cropping.
    """
    from yt_dlp import YoutubeDL
    from modules.metadata import build_ydl_options

    quality = quality or config.DEFAULT_VIDEO_QUALITY

    options = build_ydl_options(
        url,
        quiet=True,
        skip_download=True,
        format=f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]",
    )

    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        log.error(f"Stream URL resolution failed: {e}")
        if "403" in str(e):
            print(
                "\nGot an HTTP 403 Forbidden from YouTube while resolving the stream. "
                'Try updating yt-dlp:  pip install -U --pre "yt-dlp[default]"\n'
            )
        raise RuntimeError(f"Could not resolve a stream URL for this video: {e}") from e

    if "requested_formats" in info and info["requested_formats"]:
        video_fmt = next((f for f in info["requested_formats"] if f.get("vcodec") not in (None, "none")), None)
        audio_fmt = next((f for f in info["requested_formats"] if f.get("acodec") not in (None, "none")), None)
        if not video_fmt or not audio_fmt:
            raise RuntimeError("Couldn't find a usable video/audio stream for this video.")
        return video_fmt["url"], audio_fmt["url"]

    # single progressive format already has both
    return info["url"], None


def _probe_stream_durations(path) -> dict:
    """Returns {'video': seconds_or_None, 'audio': seconds_or_None} for a file's
    individual streams -- used to catch a video/audio track length mismatch
    right when a clip is created, instead of only discovering it later when
    something downstream (like an mp3 conversion) surfaces the shorter track."""
    result = {"video": None, "audio": None}
    for stream_type in ("v", "a"):
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", stream_type,
            "-show_entries", "stream=duration",
            "-of", "json", str(path),
        ]
        probe = subprocess.run(cmd, capture_output=True, text=True)
        try:
            streams = _json.loads(probe.stdout).get("streams", [])
            if streams and streams[0].get("duration"):
                result["video" if stream_type == "v" else "audio"] = float(streams[0]["duration"])
        except (_json.JSONDecodeError, ValueError, KeyError):
            pass
    return result


def _check_clip_stream_mismatch(output_path, requested_duration, context: str):
    """
    Compares the video and audio stream durations actually inside the
    finished clip against what was requested. If they disagree by more
    than 1 second, prints and logs a clear diagnostic immediately --
    at clip-creation time -- rather than leaving it to be discovered
    later (e.g. when the clip is subsequently converted to mp3 and the
    shorter audio track is all that's left to look at).
    """
    durations = _probe_stream_durations(output_path)
    video_dur, audio_dur = durations["video"], durations["audio"]

    if video_dur and audio_dur and abs(video_dur - audio_dur) > 1.0:
        msg = (
            f"Stream length mismatch in {output_path.name}: "
            f"video track is {video_dur:.2f}s but audio track is {audio_dur:.2f}s "
            f"(requested {requested_duration:.2f}s). {context}"
        )
        print(f"\nWarning: {msg}")
        log.warning(msg)
    elif video_dur and abs(video_dur - requested_duration) > 1.0:
        msg = (
            f"{output_path.name}'s video track is {video_dur:.2f}s, "
            f"but {requested_duration:.2f}s was requested. {context}"
        )
        print(f"\nWarning: {msg}")
        log.warning(msg)


def stream_crop_clip(
    url: str,
    output_path,
    start: float,
    end: float,
    aspect_ratio: str = "original",
    resolution: str = "original",
    quality: str = "high",
    target_size_mb: float = None,
    video_quality: str = None,
):
    """
    Crops [start, end] straight out of YouTube's own CDN, never
    downloading the full video to disk. -ss/-to are placed BEFORE each
    -i so ffmpeg issues an HTTP range request for just that slice
    instead of pulling the whole stream down first -- this is what
    keeps this fast even on a multi-hour source video.
    """
    video_url, audio_url = get_stream_urls(url, video_quality)
    duration = end - start
    video_filter = _build_video_filter(video_url, aspect_ratio, resolution)

    cmd = ["ffmpeg", "-y"]
    cmd += ["-ss", str(start), "-to", str(end), "-i", video_url]

    if audio_url:
        cmd += ["-ss", str(start), "-to", str(end), "-i", audio_url]
        cmd += ["-map", "0:v:0", "-map", "1:a:0"]

    if video_filter:
        cmd += ["-vf", video_filter]

    if target_size_mb:
        video_kbps = _calculate_bitrate_kbps(duration, target_size_mb)
        cmd += ["-b:v", f"{video_kbps}k", "-maxrate", f"{video_kbps}k", "-bufsize", f"{video_kbps * 2}k"]
    else:
        # No size cap given -- default to the highest practical quality
        # ("maximum stream source bitrate") rather than a moderate preset.
        crf = {"high": "18", "balanced": "23", "small": "28"}.get(quality, "18")
        cmd += ["-crf", crf, "-preset", "veryfast"]

    cmd += ["-c:v", "libx264", "-c:a", "aac", "-b:a", "128k", str(output_path)]

    log.info(f"Running stream-crop ffmpeg: {' '.join(cmd)}")
    ok, stderr_text = _run_ffmpeg_with_progress(cmd, duration, label="Processing Clip")

    if not ok:
        output_path.unlink(missing_ok=True)
        log.error(f"Stream-crop ffmpeg failed: {stderr_text[-1500:]}")
        raise RuntimeError("ffmpeg failed to stream-crop the clip. See logs/whop.log for details.")

    _check_clip_stream_mismatch(
        output_path, duration,
        context=f"Source video/audio streams were pulled separately from {url}."
    )

    return output_path


# ==========================
# CROPPING (ffmpeg, local files)
# ==========================

ASPECT_RATIOS = {
    "9:16": (9, 16),
    "1:1": (1, 1),
    "original": None,
}

RESOLUTIONS = {
    "1080p": 1080,
    "720p": 720,
    "original": None,
}


def _probe_dimensions(video_path):
    """Reads width/height with ffprobe."""
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json", str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = _json.loads(result.stdout)
    stream = data["streams"][0]
    return int(stream["width"]), int(stream["height"])


def _probe_duration(video_path) -> float:
    """Reads total duration in seconds with ffprobe -- used to drive the progress bar."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json", str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(_json.loads(result.stdout)["format"]["duration"])
    except (KeyError, ValueError, _json.JSONDecodeError):
        return 0.0


def _build_video_filter(source_path, aspect_ratio: str, resolution: str):
    filters = []

    if aspect_ratio == "9:16":
        # Letterbox, not crop -- scales the landscape frame down to fit a
        # 1080-wide vertical canvas and pads top/bottom with black bars,
        # so faces/action never get cut off the way a center-crop would.
        # Uses ffmpeg's own ow/iw/oh/ih runtime expressions, so no
        # dimension probing is needed -- works on any source, including
        # remote stream URLs.
        filters.append("scale=1080:-2,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black")

    elif aspect_ratio and aspect_ratio not in ("original", "9:16") and aspect_ratio in ASPECT_RATIOS:
        target_w_ratio, target_h_ratio = ASPECT_RATIOS[aspect_ratio]
        src_w, src_h = _probe_dimensions(source_path)
        target_ratio = target_w_ratio / target_h_ratio
        src_ratio = src_w / src_h

        if src_ratio > target_ratio:
            # source too wide -- crop the sides
            new_w = int(src_h * target_ratio)
            new_w -= new_w % 2
            filters.append(f"crop={new_w}:{src_h}:(in_w-{new_w})/2:0")
        else:
            # source too tall -- crop top/bottom
            new_h = int(src_w / target_ratio)
            new_h -= new_h % 2
            filters.append(f"crop={src_w}:{new_h}:0:(in_h-{new_h})/2")

    if resolution and resolution != "original" and resolution in RESOLUTIONS and aspect_ratio != "9:16":
        # skip for 9:16 -- the letterbox filter above already fixes the
        # output canvas size, an extra scale would fight with it
        height = RESOLUTIONS[resolution]
        filters.append(f"scale=-2:{height}")

    return ",".join(filters) if filters else None


def _calculate_bitrate_kbps(duration_seconds: float, target_size_mb: float, audio_kbps: int = 128) -> int:
    """
    Standard "target file size" bitrate math:
    total_bits = target_size_MB * 8192 (kilobits)
    video_kbps = total_kbps / duration - audio_kbps
    """
    if duration_seconds <= 0:
        return 2000  # sane fallback
    total_kbps_budget = (target_size_mb * 8192) / duration_seconds
    video_kbps = int(total_kbps_budget - audio_kbps)
    return max(video_kbps, 200)  # never go below a watchable floor


def crop_clip(
    source_path,
    output_path,
    start: float,
    end: float,
    aspect_ratio: str = "original",
    resolution: str = "original",
    quality: str = "balanced",
    target_size_mb: float = None,
):
    """
    Cuts [start, end] out of source_path and writes output_path, applying
    aspect ratio crop, resolution scale, and either a quality preset or a
    calculated bitrate to hit a target file size.
    """
    duration = end - start
    video_filter = _build_video_filter(source_path, aspect_ratio, resolution)

    cmd = ["ffmpeg", "-y", "-ss", str(start), "-i", str(source_path), "-t", str(duration)]

    if video_filter:
        cmd += ["-vf", video_filter]

    if target_size_mb:
        video_kbps = _calculate_bitrate_kbps(duration, target_size_mb)
        cmd += ["-b:v", f"{video_kbps}k", "-maxrate", f"{video_kbps}k", "-bufsize", f"{video_kbps * 2}k"]
    else:
        crf = {"high": "18", "balanced": "23", "small": "28"}.get(quality, "23")
        cmd += ["-crf", crf, "-preset", "veryfast"]

    cmd += ["-c:a", "aac", "-b:a", "128k", str(output_path)]

    log.info(f"Running ffmpeg crop: {' '.join(cmd)}")
    ok, stderr_text = _run_ffmpeg_with_progress(cmd, duration, label="Processing Clip")

    if not ok:
        output_path.unlink(missing_ok=True)
        log.error(f"ffmpeg crop failed: {stderr_text[-1000:]}")
        raise RuntimeError("ffmpeg failed to crop the clip. See logs/whop.log for details.")

    _check_clip_stream_mismatch(
        output_path, duration,
        context=f"Source file was {source_path}."
    )

    return output_path
