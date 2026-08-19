"""
Exporter: writes scenes and clip bundles to disk, and formats the
copy-paste-into-ChatGPT block for Menu Option 2.

This module ONLY writes/formats output. It never scores, downloads,
or crops -- see scorer.py and downloader.py for those.
"""

import json

from core.project import VideoProject
from core.candidate import CandidateClip
from classes.transcript_data import Transcript
from modules.utils import seconds_to_timestamp


def format_scenes_block(candidates: list) -> str:
    """
    Human-readable Top 5 block: timestamps, summary, and why it was
    picked. Meant to be printed to console and pasted into an external
    AI tool, and is also what gets saved to scenes.txt.
    """
    lines = []
    for idx, c in enumerate(candidates, start=1):
        summary = c.text.strip()
        if len(summary) > 220:
            summary = summary[:220].rsplit(" ", 1)[0] + "..."

        lines.append(f"Scene {idx}  [Score: {c.score}/10]")
        lines.append(f"  Start: {seconds_to_timestamp(int(c.start))}   End: {seconds_to_timestamp(int(c.end))}   Duration: {int(c.duration)}s")
        lines.append(f"  Summary: {summary}")
        lines.append(f"  Why: {'; '.join(c.reasons)}")
        lines.append("")

    return "\n".join(lines)


def save_scenes(project: VideoProject, candidates: list):
    """Saves scenes.json (cache, used by the cropper's cached-scene mode) and scenes.txt."""
    data = [c.to_dict() for c in candidates]
    with open(project.scenes_json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    with open(project.scenes_txt_path, "w", encoding="utf-8") as f:
        f.write(format_scenes_block(candidates))

    return project.scenes_json_path, project.scenes_txt_path


def load_scenes(project: VideoProject) -> list:
    if not project.scenes_json_path.exists():
        return []
    with open(project.scenes_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [CandidateClip.from_dict(d) for d in data]


def add_scene(project: VideoProject, candidate: CandidateClip):
    """
    Appends one manually-cropped clip's timestamps to scenes.json,
    used when the user crops a custom segment and opts to remember it.
    """
    scenes = load_scenes(project)
    scenes.append(candidate)
    save_scenes(project, scenes)
    return scenes


def export_clip_transcript(project: VideoProject, transcript: Transcript, start: float, end: float, clip_path):
    """
    Saves the .txt and .srt transcript slice that matches a cropped
    clip, next to the clip itself (same basename).
    """
    sliced = transcript.slice(start, end)
    txt_path = clip_path.with_suffix(".txt")
    srt_path = clip_path.with_suffix(".srt")
    sliced.save_txt(txt_path)
    sliced.save_srt(srt_path)
    return txt_path, srt_path
