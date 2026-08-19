"""
Storage Manager (Menu Option 4): keeps the toolkit's disk footprint
sane by managing the one thing that actually takes up space --
downloaded source videos.
"""

import shutil

import config
from core import settings as settings_module
from core.project import VideoProject
from core.logger import get_logger

log = get_logger("storage_manager")


def toggle_auto_clean() -> bool:
    """Flips auto-clean; returns the new state."""
    return settings_module.toggle("auto_clean_source_video")


def is_auto_clean_enabled() -> bool:
    return bool(settings_module.get("auto_clean_source_video"))


def maybe_auto_clean(project: VideoProject):
    """
    Called right after a successful crop. Deletes source.mp4 if
    auto-clean is on, keeping transcript/scenes/clips intact.
    """
    if is_auto_clean_enabled() and project.has_source_video():
        project.source_video_path.unlink(missing_ok=True)
        print(f"Auto-clean: deleted source video for '{project.title}'")
        log.info(f"Auto-clean deleted source video for {project.title}")


def clear_video_cache() -> list:
    """
    Deletes ONLY large source video files across every project,
    keeping transcripts, scenes, and cropped clips intact.
    Returns the list of project titles that were cleaned.
    """
    cleaned = []
    for folder_name in VideoProject.list_all():
        project = VideoProject.load(folder_name)
        if project.has_source_video():
            size_mb = project.source_video_path.stat().st_size / (1024 * 1024)
            project.source_video_path.unlink(missing_ok=True)
            cleaned.append((project.title, round(size_mb, 1)))
            log.info(f"Cleared source video for {project.title} ({size_mb:.1f} MB)")
    return cleaned


def deep_clean(folder_name: str):
    """Deletes an entire project folder -- transcript, scenes, clips, everything."""
    folder = config.PROJECTS_FOLDER / folder_name
    if not folder.exists():
        raise FileNotFoundError(f"No project folder named '{folder_name}'")
    shutil.rmtree(folder)
    log.info(f"Deep cleaned project folder: {folder_name}")
