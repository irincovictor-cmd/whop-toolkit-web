"""
CandidateClip: one potential short-form clip found inside a video.

analyzer.py creates these (unscored).
scorer.py fills in .score, .subscores, and .reasons.
exporter.py writes them to disk.
downloader.py cuts them from the source video.
"""

from dataclasses import dataclass, field, asdict


@dataclass
class CandidateClip:
    start: float
    end: float
    text: str
    tags: list = field(default_factory=list)       # e.g. ["hook", "story"]
    score: float = 0.0
    subscores: dict = field(default_factory=dict)   # e.g. {"hook": 8.5, ...}
    reasons: list = field(default_factory=list)     # human-readable explanations

    @property
    def duration(self) -> float:
        return round(self.end - self.start, 2)

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "CandidateClip":
        return CandidateClip(
            start=float(data["start"]),
            end=float(data["end"]),
            text=data.get("text", ""),
            tags=data.get("tags", []),
            score=float(data.get("score", 0.0)),
            subscores=data.get("subscores", {}),
            reasons=data.get("reasons", []),
        )
