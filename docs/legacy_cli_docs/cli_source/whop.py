"""
Whop Toolkit -- CLI entry point.

    python whop.py

No GUI, no database. Everything lives on disk: full projects (with
transcripts) under projects/<video title>/, and fast direct-to-clip
output under quick_clips/. See docs/USER_GUIDE.md for setup and
docs/DEVELOPER_GUIDE.md for how the pieces fit together.
"""

import os
import warnings

# Suppress Hugging Face symlink and token warnings in the terminal, and
# disable symlink usage entirely -- on Windows, creating symlinks requires
# elevated privileges, and huggingface_hub's default caching falls back to
# symlinks during faster-whisper model downloads, which crashes standard
# (non-admin) Windows accounts with WinError 1314. Disabling symlinks makes
# it copy files instead, which works for every user account.
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub")

import sys
import time
import shutil
from pathlib import Path

import config
from core.project import VideoProject
from core.logger import get_logger
from core import activity_log

from modules import metadata, transcript, downloader, converter
from modules import utils
from modules.utils import ask_choice, ask_yes_no
from modules import clip_selector

log = get_logger("main")

# In-memory session state -- lasts only for this run of the program.
# Set by Option 1 (Extract Transcript) so Option 3 (Quick Stream-Crop)
# can jump straight to timestamps without re-asking for the video.
_session_video = None  # {"source_type": "youtube"/"local", "url": ..., "path": ..., "duration": ...}


# ==========================
# PROJECT SELECTION (Option 1)
# ==========================

def get_or_create_project() -> VideoProject:
    """
    Main way in for a full project (transcript + cache): ask whether
    this is a YouTube video or a file the user already has, then
    fetch/import accordingly. Reuses the project if this video's been
    seen before.
    """
    source = ask_choice("\nWhere's the video coming from?", ["YouTube URL", "A file I already have"])

    if source == "YouTube URL":
        return _get_or_create_project_from_url()
    return _get_or_create_project_from_file()


def _get_or_create_project_from_url() -> VideoProject:
    url = input("\nPaste a YouTube URL: ").strip()
    if not url:
        return None

    print("Fetching video info...")
    try:
        info = metadata.fetch_metadata(url)
    except Exception as e:
        print(f"Couldn't fetch that video: {e}")
        return None

    existing = VideoProject.find_by_video_id(info["video_id"])
    if existing:
        choice = ask_choice(
            f"\nYou've already got a project for '{existing.title}'. What do you want to do?",
            ["Continue with the existing project", "Refresh metadata and continue"],
        )
        if choice.startswith("Refresh"):
            existing.title = info["title"]
            existing.duration = info["duration"]
            existing.uploader = info["uploader"]
            existing.save_info()
            print("Metadata refreshed.")
        return existing

    project = VideoProject(
        title=info["title"],
        url=info["url"],
        video_id=info["video_id"],
        duration=info["duration"],
        uploader=info["uploader"],
        source_type="youtube",
    )
    project.create()
    project.save_info()

    print(f"Created new project: {project.title}")
    return project


def _get_or_create_project_from_file() -> VideoProject:
    path = utils.prompt_file_path("Where's the video file?")
    if not path:
        return None

    print("Reading file info...")
    try:
        info = metadata.fetch_local_metadata(path)
    except Exception as e:
        print(f"Couldn't read that file: {e}")
        return None

    project = VideoProject(
        title=info["title"],
        url=info["url"],
        video_id=info["video_id"],
        duration=info["duration"],
        uploader=info["uploader"],
        source_type="local",
    )

    is_new = not project.project_folder.exists()
    project.create()
    project.save_info()

    try:
        downloader.import_local_video(project, info["local_path"])
    except RuntimeError as e:
        print(f"Import failed: {e}")
        return None

    print(f"{'Created new' if is_new else 'Reusing existing'} project: {project.title}")
    return project


def pick_existing_project() -> VideoProject:
    """Used by the Storage Manager to list known projects."""
    pairs = VideoProject.list_all_with_titles()
    if not pairs:
        print("\nNo projects yet -- fetch a video first (Option 1).")
        return None

    titles = [title for _, title in pairs]
    chosen_title = ask_choice("\nWhich video?", titles)
    folder_name = next(f for f, t in pairs if t == chosen_title)
    return VideoProject.load(folder_name)


def _quick_clip_output_path(title: str) -> Path:
    """Unique output path under quick_clips/ for the direct-to-clip flows."""
    safe_title = "".join(c for c in title if c not in r'\/:*?"<>|').strip() or "clip"
    return config.QUICK_CLIPS_FOLDER / f"{safe_title}_{int(time.time())}.mp4"


# ==========================
# OPTION 1: EXTRACT TRANSCRIPT
# ==========================

def menu_extract_transcript():
    global _session_video

    project = get_or_create_project()
    if not project:
        return

    if project.has_transcript() and not ask_yes_no("Transcript already exists -- re-run anyway?", default=False):
        print("Using cached transcript.")
        activity_log.log_activity("Viewed cached transcript", project.title)
    else:
        model_size = clip_selector.prompt_whisper_model()
        try:
            transcript.get_transcript(project, model_size=model_size, force=True)
        except RuntimeError as e:
            print(f"\nTranscription failed: {e}")
            return

        print(f"\nSaved transcript to: {project.transcripts_folder}")
        print("  - transcript.txt  (clean text -- copy-paste straight into ChatGPT/Claude)")
        print("  - transcript.srt")
        activity_log.log_activity("Generated transcript", project.title)

    # Remember this video for Option 3's session-memory shortcut.
    if project.is_local:
        _session_video = {
            "source_type": "local",
            "path": str(project.source_video_path),
            "duration": project.duration,
            "title": project.title,
        }
    else:
        _session_video = {
            "source_type": "youtube",
            "url": project.url,
            "duration": project.duration,
            "title": project.title,
        }


# ==========================
# OPTION 2: DIRECT YOUTUBE VIDEO CLIPPER
# ==========================

def menu_direct_clipper():
    url = input("\nPaste a YouTube URL: ").strip()
    if not url:
        return

    print("Fetching video duration...")
    try:
        info = metadata.fetch_metadata(url)
    except Exception as e:
        print(f"Couldn't fetch that video: {e}")
        return

    print(f"'{info['title']}' -- {int(info['duration'])}s long.")
    start, end = clip_selector.prompt_manual_timestamps(duration=info["duration"])
    settings = clip_selector.prompt_format_and_size()

    output_path = _quick_clip_output_path(info["title"])

    print("\nStream-cropping directly from YouTube (no full download)...")
    try:
        downloader.stream_crop_clip(
            url=info["url"],
            output_path=output_path,
            start=start,
            end=end,
            **settings,
        )
    except RuntimeError as e:
        print(f"\n{e}")
        return

    print(f"Saved clip: {output_path}")
    activity_log.log_activity(f"Direct-clipped YouTube video ({int(start)}s-{int(end)}s)", info["title"])


# ==========================
# OPTION 3: QUICK STREAM-CROP
# ==========================

def menu_quick_stream_crop():
    global _session_video

    if _session_video is not None:
        source = _session_video
        print(f"\nUsing active video from this session: {source['title']}")
    else:
        path = utils.prompt_file_path("No active video found. Where's the file?")

        if not path or not os.path.exists(path):
            print("That file path doesn't exist.")
            return

        print("Reading file info...")
        try:
            info = metadata.fetch_local_metadata(path)
        except Exception as e:
            print(f"Couldn't read that file: {e}")
            return

        source = {
            "source_type": "local",
            "path": info["local_path"],
            "duration": info["duration"],
            "title": info["title"],
        }

    start, end = clip_selector.prompt_manual_timestamps(duration=source["duration"])
    settings = clip_selector.prompt_format_and_size()

    output_path = _quick_clip_output_path(source["title"])

    print("\nCropping...")
    try:
        if source["source_type"] == "local":
            downloader.crop_clip(
                source_path=source["path"],
                output_path=output_path,
                start=start,
                end=end,
                **settings,
            )
        else:
            downloader.stream_crop_clip(
                url=source["url"],
                output_path=output_path,
                start=start,
                end=end,
                **settings,
            )
    except RuntimeError as e:
        print(f"\n{e}")
        return

    print(f"Saved clip: {output_path}")
    activity_log.log_activity(f"Quick stream-cropped ({int(start)}s-{int(end)}s)", source["title"])


# ==========================
# OPTION 4: SMART MEDIA CONVERTER
# ==========================

def menu_media_converter():
    path = utils.prompt_file_path("Which file do you want to convert?")

    if not path or not os.path.exists(path):
        print("That file path doesn't exist.")
        return

    media_type = converter.detect_media_type(path)
    if media_type is None:
        _, ext = os.path.splitext(path)
        print(f"'{ext or '(no extension)'}' isn't a recognized video or audio format.")
        return

    if media_type == "video":
        menu = converter.VIDEO_MENU
        prompt = "\nVideo file detected. Convert to:"
    else:
        menu = converter.AUDIO_MENU
        prompt = "\nAudio file detected. Convert to:"

    labels = [label for label, _, _ in menu]
    choice_label = ask_choice(prompt, labels)
    chosen_entry = next(entry for entry in menu if entry[0] == choice_label)

    print("\nConverting...")
    try:
        output_path = converter.convert_file(path, chosen_entry)
    except RuntimeError as e:
        print(f"\n{e}")
        return

    print(f"Saved: {output_path}")
    activity_log.log_activity(f"Converted media ({choice_label})", Path(path).name)


# ==========================
# MAIN LOOP
# ==========================

def main():
    if shutil.which("ffmpeg") is None:
        print("FFmpeg isn't installed or isn't on your PATH.")
        print("See docs/USER_GUIDE.md for install steps (Windows and Mac).")
        sys.exit(1)

    activity_log.print_welcome_message()

    while True:
        choice = ask_choice(
            "\n=== Whop Toolkit ===",
            [
                "Extract Transcript (Get clean text to copy-paste into AI)",
                "Direct YouTube Video Clipper (Fast clip download by URL + Timestamps)",
                "Quick Stream-Crop (Crop via manual timestamps or Drag-and-Drop file)",
                "Smart Media Converter (Convert video/audio formats)",
                "Exit",
            ],
        )

        try:
            if choice.startswith("Extract Transcript"):
                menu_extract_transcript()
            elif choice.startswith("Direct YouTube"):
                menu_direct_clipper()
            elif choice.startswith("Quick Stream-Crop"):
                menu_quick_stream_crop()
            elif choice.startswith("Smart Media Converter"):
                menu_media_converter()
            elif choice.startswith("Exit"):
                print("See you next time.")
                sys.exit(0)
        except KeyboardInterrupt:
            print("\n\nCancelled.")
        except SystemExit:
            raise
        except Exception as e:
            log.exception(f"Error in menu action: {choice}")
            print(f"\nSomething went wrong: {e}")
            print("Returning to the main menu. Details saved to logs/whop.log")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted -- see you next time.")
        sys.exit(0)
    except Exception as e:
        log.exception("Unhandled error in main loop")
        print(f"\nSomething went wrong: {e}")
        print("Details were saved to logs/whop.log")
        sys.exit(1)
