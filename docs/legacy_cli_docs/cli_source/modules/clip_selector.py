"""
CLI interaction for the Video Cropper (Menu Option 3).

This module ONLY gathers input from the user via prompts. It never
touches ffmpeg, yt-dlp, or the filesystem beyond reading what
exporter.py already saved.
"""

from modules.utils import ask_choice, ask_yes_no, timestamp_to_seconds
from modules.downloader import ASPECT_RATIOS, RESOLUTIONS


def prompt_crop_mode() -> str:
    return ask_choice(
        "\nHow do you want to crop this video?",
        ["Cached scene (pick from Top 5)", "Manual timestamps"],
    ).split(" ")[0].lower()  # "cached" or "manual"


def prompt_scene_number(max_scenes: int) -> int:
    while True:
        raw = input(f"Which scene number (1-{max_scenes})? > ").strip()
        try:
            n = int(raw)
            if 1 <= n <= max_scenes:
                return n - 1  # zero-indexed
        except ValueError:
            pass
        print(f"Enter a number between 1 and {max_scenes}.")


def prompt_manual_timestamps(duration: float = None):
    """
    Accepts either HH:MM:SS or raw seconds. When `duration` (the source
    video's total length in seconds) is known, validates that neither
    timestamp exceeds it -- an end time past the actual video length
    would otherwise hand ffmpeg a nonsensical range and produce a
    corrupted or truncated clip.
    """
    def parse(raw: str) -> float:
        raw = raw.strip()
        if ":" in raw:
            return float(timestamp_to_seconds(raw))
        return float(raw)

    while True:
        try:
            start_raw = input("Start timestamp (HH:MM:SS or seconds): ").strip()
            end_raw = input("End timestamp (HH:MM:SS or seconds): ").strip()
            start = parse(start_raw)
            end = parse(end_raw)

            if end <= start:
                print("End must be after start.")
                continue

            if duration is not None and (start < 0 or end > duration):
                print(f"This video is only {int(duration)}s long -- both timestamps must fall within that.")
                continue

            return start, end
        except ValueError:
            print("Couldn't parse that -- use HH:MM:SS or plain seconds.")


def prompt_export_settings():
    aspect_ratio = ask_choice(
        "\nAspect ratio:",
        list(ASPECT_RATIOS.keys()),
        default_index=list(ASPECT_RATIOS.keys()).index("original"),
    )
    resolution = ask_choice(
        "\nResolution:",
        list(RESOLUTIONS.keys()),
        default_index=list(RESOLUTIONS.keys()).index("original"),
    )
    quality = ask_choice(
        "\nQuality preset:",
        ["high", "balanced", "small"],
        default_index=1,
    )

    target_size_mb = None
    if ask_yes_no("\nSet a target file size limit (e.g. for a 50MB upload cap)?", default=False):
        while True:
            raw = input("Target size in MB: ").strip()
            try:
                target_size_mb = float(raw)
                break
            except ValueError:
                print("Enter a number, e.g. 50")

    return {
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
        "quality": quality,
        "target_size_mb": target_size_mb,
    }


def prompt_save_manual_to_cache() -> bool:
    return ask_yes_no("Save this clip's timestamps to the scene cache for next time?", default=True)


def prompt_format_and_size():
    """
    Simplified export prompt for the direct-to-clip flows (Options 2/3):
    just format (vertical/landscape) and an optional size cap. Replaces
    the old three-question aspect/resolution/quality prompt for these
    fast paths -- full control is still available via prompt_export_settings()
    if a slower, project-based flow needs it.
    """
    format_choice = ask_choice(
        "\nFormat:",
        ["Vertical 9:16 (letterboxed, no crop)", "Landscape 16:9 (original layout)"],
        default_index=1,
    )
    aspect_ratio = "9:16" if format_choice.startswith("Vertical") else "original"

    target_size_mb = None
    if ask_yes_no("\nSet a target file size cap in MB?", default=False):
        while True:
            raw = input("Target size in MB: ").strip()
            try:
                target_size_mb = float(raw)
                break
            except ValueError:
                print("Enter a number, e.g. 50")

    return {
        "aspect_ratio": aspect_ratio,
        "resolution": "original",
        # No cap chosen -> default to the highest practical quality
        # ("maximum stream source bitrate") rather than a middling preset.
        "quality": "high",
        "target_size_mb": target_size_mb,
    }


def prompt_whisper_model() -> str:
    return ask_choice(
        "\nWhisper model (only used if this video has no YouTube captions):",
        ["base (fast)", "small (balanced)", "medium (high accuracy)"],
        default_index=0,
    ).split(" ")[0]


def prompt_clip_length_range():
    """
    Lets the user constrain how long candidate scenes can be before
    Menu Option 2 scores them -- so a 2-hour podcast doesn't just hand
    back five 90-second blocks when the user wants punchy 15-30s hooks.
    Returns (min_length, max_length) in seconds.
    """
    choice = ask_choice(
        "\nWhat length of highlights are you looking for?",
        ["Short (15-30s)", "Medium (30-60s)", "Long (60-90s)", "Custom range"],
        default_index=1,
    )

    presets = {
        "Short (15-30s)": (15, 30),
        "Medium (30-60s)": (30, 60),
        "Long (60-90s)": (60, 90),
    }

    if choice in presets:
        return presets[choice]

    while True:
        try:
            min_len = int(input("Minimum clip length in seconds: ").strip())
            max_len = int(input("Maximum clip length in seconds: ").strip())
            if 0 < min_len < max_len:
                return min_len, max_len
            print("Minimum must be positive and less than maximum.")
        except ValueError:
            print("Enter whole numbers, e.g. 20")
