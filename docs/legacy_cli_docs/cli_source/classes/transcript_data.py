"""
Data structures for transcripts.

A Transcript is source-agnostic: it looks the same whether it came
from YouTube's captions or from a local Whisper run. Everything
downstream (analyzer, scorer, exporter) only ever talks to this class,
never to youtube_transcript_api or faster-whisper directly.
"""

from dataclasses import dataclass, field, asdict
import json
from pathlib import Path


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str

    @property
    def duration(self) -> float:
        return round(self.end - self.start, 2)

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "TranscriptSegment":
        return TranscriptSegment(
            start=float(data["start"]),
            end=float(data["end"]),
            text=data["text"],
        )


@dataclass
class Transcript:
    language: str
    source: str  # "youtube" or "whisper"
    segments: list = field(default_factory=list)  # list[TranscriptSegment]

    @property
    def full_text(self) -> str:
        return " ".join(seg.text.strip() for seg in self.segments)

    @property
    def duration(self) -> float:
        if not self.segments:
            return 0.0
        return round(self.segments[-1].end, 2)

    def segments_between(self, start: float, end: float) -> list:
        """Return every segment that overlaps the [start, end] window."""
        return [
            seg for seg in self.segments
            if seg.end > start and seg.start < end
        ]

    def text_between(self, start: float, end: float) -> str:
        return " ".join(seg.text.strip() for seg in self.segments_between(start, end))

    def to_dict(self) -> dict:
        return {
            "language": self.language,
            "source": self.source,
            "segments": [seg.to_dict() for seg in self.segments],
        }

    @staticmethod
    def from_dict(data: dict) -> "Transcript":
        return Transcript(
            language=data.get("language", "unknown"),
            source=data.get("source", "unknown"),
            segments=[TranscriptSegment.from_dict(s) for s in data.get("segments", [])],
        )

    def save_json(self, path: Path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @staticmethod
    def load_json(path: Path) -> "Transcript":
        with open(path, "r", encoding="utf-8") as f:
            return Transcript.from_dict(json.load(f))

    def save_txt(self, path: Path):
        """Human-readable [HH:MM:SS] text line format."""
        from modules.utils import seconds_to_timestamp

        with open(path, "w", encoding="utf-8") as f:
            for seg in self.segments:
                f.write(f"[{seconds_to_timestamp(int(seg.start))}] {seg.text.strip()}\n")

    def save_srt(self, path: Path):
        """Standard .srt subtitle file, editing-software compatible."""
        def srt_time(t: float) -> str:
            hours = int(t // 3600)
            minutes = int((t % 3600) // 60)
            secs = int(t % 60)
            millis = int(round((t - int(t)) * 1000))
            return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

        with open(path, "w", encoding="utf-8") as f:
            for i, seg in enumerate(self.segments, start=1):
                f.write(f"{i}\n")
                f.write(f"{srt_time(seg.start)} --> {srt_time(seg.end)}\n")
                f.write(f"{seg.text.strip()}\n\n")

    def slice(self, start: float, end: float) -> "Transcript":
        """Returns a new Transcript containing only segments in [start, end],
        with times re-based to start at 0 -- used when exporting a clip's
        matching transcript/subtitles alongside the cropped video."""
        sliced_segments = []
        for seg in self.segments_between(start, end):
            new_start = max(0.0, seg.start - start)
            new_end = max(new_start, seg.end - start)
            sliced_segments.append(TranscriptSegment(new_start, new_end, seg.text))
        return Transcript(language=self.language, source=self.source, segments=sliced_segments)
