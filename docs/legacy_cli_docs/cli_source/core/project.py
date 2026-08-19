from pathlib import Path
import json
from datetime import datetime

import config


class VideoProject:
    """
    Represents a single video project (YouTube or local upload).

    Every downloaded transcript, clip, report, and log belongs to one
    VideoProject. One folder per video, under projects/<video_id>/.

    Folders are keyed by video_id (YouTube's own ID, or a hash of the
    file path for local uploads) rather than the video's title. Titles
    can change on YouTube's end (edits, trailing whitespace, unicode
    differences) -- an ID doesn't, so this is what prevents the same
    video from silently getting a second, duplicate project folder.
    The human-readable title is still stored in info.json and used
    everywhere the user actually sees a project listed.
    """

    def __init__(self, title, url, video_id, duration, uploader, source_type="youtube"):
        self.title = title
        self.url = url                  # None for local uploads
        self.video_id = video_id
        self.duration = duration
        self.uploader = uploader
        self.source_type = source_type  # "youtube" or "local"

        safe_id = "".join(c for c in str(video_id) if c not in r'\/:*?"<>|').strip() or "unknown"

        self.project_folder = config.PROJECTS_FOLDER / safe_id
        # alias kept for backwards compatibility with older module code
        self.project_path = self.project_folder

        self.clips_folder = self.project_folder / "clips"
        self.reports_folder = self.project_folder / "reports"
        self.transcripts_folder = self.project_folder / "transcripts"

        # Well-known file paths inside the project
        self.info_path = self.project_folder / "info.json"
        self.transcript_json_path = self.transcripts_folder / "transcript.json"
        self.transcript_txt_path = self.transcripts_folder / "transcript.txt"
        self.transcript_srt_path = self.transcripts_folder / "transcript.srt"
        self.scenes_json_path = self.project_folder / "scenes.json"
        self.scenes_txt_path = self.project_folder / "scenes.txt"
        self.source_video_path = self.project_folder / f"source.{config.PREFERRED_FORMAT}"
        self.source_audio_path = self.project_folder / "audio.mp3"

    def create(self):
        """Creates the project folders (safe to call every run)."""
        self.project_folder.mkdir(parents=True, exist_ok=True)
        self.clips_folder.mkdir(exist_ok=True)
        self.reports_folder.mkdir(exist_ok=True)
        self.transcripts_folder.mkdir(exist_ok=True)

    def save_info(self):
        """Saves project information into info.json"""
        info = {
            "title": self.title,
            "url": self.url,
            "video_id": self.video_id,
            "duration": self.duration,
            "uploader": self.uploader,
            "source_type": self.source_type,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        with open(self.info_path, "w", encoding="utf-8") as f:
            json.dump(info, f, indent=4, ensure_ascii=False)

    @staticmethod
    def load(folder_name: str) -> "VideoProject":
        """
        Rebuilds a VideoProject from an existing projects/<folder_name>/info.json.
        Used by the CLI when the user picks an already-downloaded video
        instead of pasting a new URL.
        """
        folder = config.PROJECTS_FOLDER / folder_name
        info_path = folder / "info.json"
        with open(info_path, "r", encoding="utf-8") as f:
            info = json.load(f)

        project = VideoProject(
            title=info["title"],
            url=info["url"],
            video_id=info["video_id"],
            duration=info["duration"],
            uploader=info["uploader"],
            source_type=info.get("source_type", "youtube"),  # old projects predate this field
        )
        project.create()
        return project

    @staticmethod
    def find_by_video_id(video_id: str) -> "VideoProject":
        """
        Looks up an existing project by its platform video_id, regardless
        of what its folder happens to be named -- this is what makes
        re-pasting the same URL reuse the existing project instead of
        creating a duplicate, and it also works for projects created
        before this lookup existed (their folder was named after the
        title, but info.json always had video_id).
        Returns None if no match is found.
        """
        if not config.PROJECTS_FOLDER.exists():
            return None

        for folder in config.PROJECTS_FOLDER.iterdir():
            info_path = folder / "info.json"
            if not info_path.exists():
                continue
            try:
                with open(info_path, "r", encoding="utf-8") as f:
                    info = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
            if info.get("video_id") == video_id:
                return VideoProject.load(folder.name)

        return None

    @staticmethod
    def list_all() -> list:
        """Returns folder names of every existing project, newest first."""
        if not config.PROJECTS_FOLDER.exists():
            return []
        folders = [
            p for p in config.PROJECTS_FOLDER.iterdir()
            if p.is_dir() and (p / "info.json").exists()
        ]
        folders.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return [p.name for p in folders]

    @staticmethod
    def list_all_with_titles() -> list:
        """
        Returns (folder_name, title) pairs, newest first -- used anywhere
        the CLI needs to show a human-readable list. Folder names are
        video IDs now, not titles, so listing raw folder names isn't
        useful for a picker the way it used to be.
        """
        pairs = []
        for folder_name in VideoProject.list_all():
            info_path = config.PROJECTS_FOLDER / folder_name / "info.json"
            try:
                with open(info_path, "r", encoding="utf-8") as f:
                    info = json.load(f)
                pairs.append((folder_name, info.get("title", folder_name)))
            except (json.JSONDecodeError, OSError):
                pairs.append((folder_name, folder_name))
        return pairs

    def has_transcript(self) -> bool:
        return self.transcript_json_path.exists()

    def has_scenes(self) -> bool:
        return self.scenes_json_path.exists()

    def has_source_video(self) -> bool:
        return self.source_video_path.exists()

    @property
    def is_local(self) -> bool:
        return self.source_type == "local"

    def __str__(self):
        return f"{self.title} ({self.video_id})"
