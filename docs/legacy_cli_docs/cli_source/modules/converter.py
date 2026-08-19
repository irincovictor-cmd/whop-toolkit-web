"""
Smart Media Converter (Option 4): auto-detects whether a dropped file is
video or audio and routes to the matching conversion sub-menu, then runs
one of a fixed set of known-good ffmpeg recipes.

This module ONLY builds and runs ffmpeg commands for format conversion.
It never touches yt-dlp, transcripts, or the projects/ system -- inputs
are always a local file path, outputs always land in config.CONVERTED_FOLDER.
"""

import os
import time
from pathlib import Path

import config
from core.logger import get_logger
from modules.downloader import _run_ffmpeg_with_progress, _probe_duration

log = get_logger("converter")

VIDEO_EXTENSIONS = {".mov", ".mkv", ".avi", ".flv", ".webm", ".wmv", ".mp4"}
AUDIO_EXTENSIONS = {".wav", ".aac", ".m4a", ".flac", ".ogg", ".mp3"}


def detect_media_type(path: str) -> str:
    """Returns 'video', 'audio', or None if the extension isn't recognized."""
    _, ext = os.path.splitext(path)
    ext = ext.lower()
    if ext in VIDEO_EXTENSIONS:
        return "video"
    if ext in AUDIO_EXTENSIONS:
        return "audio"
    return None


def _output_path(input_path: str, new_ext: str) -> Path:
    """
    <original name>_converted.<ext> in config.CONVERTED_FOLDER, to avoid
    ever overwriting the source file. Falls back to a timestamp suffix
    on the rare chance that exact name is already taken.
    """
    stem = Path(input_path).stem
    out = config.CONVERTED_FOLDER / f"{stem}_converted{new_ext}"
    if out.exists():
        out = config.CONVERTED_FOLDER / f"{stem}_converted_{int(time.time())}{new_ext}"
    return out


# ==========================
# FFMPEG COMMAND CORES
# ==========================
# Each builder takes (input_path, output_path) and returns the full
# ffmpeg argv list. Kept as one-recipe-per-function so the routing menus
# below just pick a builder off a table -- no branching logic buried in
# the menu prompts themselves.

def _video_to_mp4(input_path, output_path):
    return ["ffmpeg", "-y", "-i", str(input_path),
            "-c:v", "libx264", "-crf", "20", "-c:a", "aac",
            "-vf", "format=yuv420p", str(output_path)]


def _video_to_mkv(input_path, output_path):
    # Fast stream copy -- no re-encode, just repackages into a new container.
    return ["ffmpeg", "-y", "-i", str(input_path), "-c", "copy", str(output_path)]


def _video_to_webm(input_path, output_path):
    return ["ffmpeg", "-y", "-i", str(input_path),
            "-c:v", "libvpx-vp9", "-crf", "30", "-b:v", "0", "-c:a", "libopus",
            str(output_path)]


def _extract_mp3(input_path, output_path):
    return ["ffmpeg", "-y", "-i", str(input_path),
            "-vn", "-acodec", "libmp3lame", "-q:a", "2", str(output_path)]


def _extract_wav_from_video(input_path, output_path):
    return ["ffmpeg", "-y", "-i", str(input_path),
            "-vn", "-acodec", "pcm_s16le", str(output_path)]


def _audio_to_mp3(input_path, output_path):
    return ["ffmpeg", "-y", "-i", str(input_path),
            "-acodec", "libmp3lame", "-q:a", "2", str(output_path)]


def _audio_to_aac(input_path, output_path):
    return ["ffmpeg", "-y", "-i", str(input_path),
            "-c:a", "aac", "-b:a", "192k", str(output_path)]


def _audio_to_wav(input_path, output_path):
    return ["ffmpeg", "-y", "-i", str(input_path),
            "-acodec", "pcm_s16le", str(output_path)]


# ==========================
# ROUTING TABLES
# ==========================
# (menu label, output extension, command builder)

VIDEO_MENU = [
    ("Convert to Universal Web MP4 Video (H.264 / AAC)", ".mp4", _video_to_mp4),
    ("Convert to Matroska Video (.mkv)", ".mkv", _video_to_mkv),
    ("Convert to WebM (.webm)", ".webm", _video_to_webm),
    ("Extract Audio Track Only (.mp3)", ".mp3", _extract_mp3),
    ("Extract High-Res Audio Track Only (.wav)", ".wav", _extract_wav_from_video),
]

AUDIO_MENU = [
    ("Convert to Compressed MP3 Audio", ".mp3", _audio_to_mp3),
    ("Convert to Standard AAC/M4A Audio", ".m4a", _audio_to_aac),
    ("Convert to High-Res Lossless WAV Audio", ".wav", _audio_to_wav),
]


def convert_file(input_path: str, menu_entry: tuple):
    """
    Runs the ffmpeg command for the chosen menu_entry (one row from
    VIDEO_MENU/AUDIO_MENU) against input_path, with the shared live
    progress bar. Returns the output Path.
    """
    label, new_ext, builder = menu_entry
    output_path = _output_path(input_path, new_ext)

    duration = _probe_duration(input_path)
    cmd = builder(input_path, output_path)

    log.info(f"Running conversion ({label}): {' '.join(cmd)}")
    ok, stderr_text = _run_ffmpeg_with_progress(cmd, duration, label="Converting")

    if not ok:
        output_path.unlink(missing_ok=True)
        log.error(f"Conversion failed: {stderr_text[-1500:]}")
        raise RuntimeError("ffmpeg failed to convert this file. See logs/whop.log for details.")

    # Audio-extraction outputs (mp3/wav from a video) can legitimately come
    # out shorter than the source's overall duration -- this isn't
    # necessarily a conversion bug, it usually means the source video's
    # audio track was already shorter than its video track (common with
    # merged adaptive-stream downloads, screen recordings, or phone video
    # with encoder start delay). Flag it clearly instead of staying silent,
    # so it doesn't look like the toolkit silently lost audio.
    if duration > 0:
        output_duration = _probe_duration(output_path)
        gap = duration - output_duration
        if gap > 1.0:
            print(
                f"\nNote: the source is {duration:.1f}s but the extracted audio is "
                f"{output_duration:.1f}s ({gap:.1f}s shorter). This usually means the "
                f"source file's audio track was already shorter than its video track "
                f"-- common in merged/downloaded video -- not data lost during conversion."
            )
            log.warning(
                f"Duration mismatch on conversion: source={duration:.2f}s "
                f"output={output_duration:.2f}s gap={gap:.2f}s ({label})"
            )

    return output_path
