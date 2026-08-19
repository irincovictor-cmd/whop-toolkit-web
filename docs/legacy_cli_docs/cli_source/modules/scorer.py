"""
Scorer: assigns a score + human-readable reasons to each CandidateClip.

Offline heuristic only -- no API calls, no cost, works immediately.
Rule-based on hook phrasing, curiosity gaps, emotional/story language,
how close the clip is to the ideal length, and whether it starts/ends
on a natural pause.

This module ONLY scores. It never downloads, crops, or writes files.
"""

import re

import config
from core.candidate import CandidateClip

TOP_SCENES_COUNT = 5

HOOK_PATTERNS = [
    r"\bwhy\b", r"\bhow\b", r"\bwhat if\b", r"\bnobody\b", r"\bnever\b",
    r"\bthe truth is\b", r"\btruth is\b", r"\bhere's the thing\b",
    r"\blisten\b", r"\bimagine\b", r"\bthe biggest\b", r"\bbiggest mistake\b",
    r"\bsecret\b", r"\bmistake\b", r"\bno one tells you\b", r"\bi used to\b",
]

CURIOSITY_PATTERNS = [
    r"\bbut then\b", r"\bturns out\b", r"\bthat's when\b", r"\bso i\b",
    r"\band that's\b", r"\bthe reason\b", r"\bwhat happened\b", r"\?\s*$",
]

EMOTION_WORDS = [
    "insane", "crazy", "shocking", "unbelievable", "terrifying", "amazing",
    "furious", "devastated", "heartbroken", "hilarious", "brutal", "wild",
    "scared", "afraid", "excited", "love", "hate", "fear",
]

STORY_PATTERNS = [
    r"\bone time\b", r"\bso basically\b", r"\blet me tell you\b",
    r"\bi remember\b", r"\btrue story\b", r"\bback when\b",
]


def _count_matches(patterns, text_lower) -> int:
    return sum(1 for p in patterns if re.search(p, text_lower))


def _score_one(candidate: CandidateClip, ideal_length: float = None, max_length: float = None) -> CandidateClip:
    ideal_length = ideal_length or config.IDEAL_CLIP_LENGTH
    max_length = max_length or config.MAX_CLIP_LENGTH

    text_lower = candidate.text.lower()
    reasons = []
    subscores = {}

    hook_hits = _count_matches(HOOK_PATTERNS, text_lower)
    subscores["hook"] = min(hook_hits, 3) * 3.3
    if hook_hits:
        reasons.append("Opens with hook-style language")
        candidate.tags.append("hook")

    curiosity_hits = _count_matches(CURIOSITY_PATTERNS, text_lower)
    subscores["curiosity"] = min(curiosity_hits, 3) * 3.3
    if curiosity_hits:
        reasons.append("Creates a curiosity gap / open loop")

    emotion_hits = sum(1 for w in EMOTION_WORDS if w in text_lower)
    subscores["emotion"] = min(emotion_hits, 3) * 3.3
    if emotion_hits:
        reasons.append("Uses emotionally charged language")
        candidate.tags.append("emotional")

    story_hits = _count_matches(STORY_PATTERNS, text_lower)
    subscores["story"] = min(story_hits, 3) * 3.3
    if story_hits:
        reasons.append("Reads as a self-contained story/anecdote")
        candidate.tags.append("story")

    # length fit: 10 at the ideal length, tapering off toward min/max
    length_diff = abs(candidate.duration - ideal_length)
    length_span = max(max_length - ideal_length, 1)
    subscores["length_fit"] = max(0.0, 10 - (length_diff / length_span) * 10)
    if subscores["length_fit"] >= 7:
        reasons.append(f"Good length for short-form ({int(candidate.duration)}s)")

    subscores["pause_boundary"] = 6.0  # baseline; analyzer already snaps to pauses where possible

    weights = config.SCORE_WEIGHTS
    total = sum(subscores[k] * weights.get(k, 1.0) for k in subscores)
    max_possible = sum(10 * weights.get(k, 1.0) for k in subscores)
    normalized = round((total / max_possible) * 10, 2) if max_possible else 0.0

    candidate.subscores = subscores
    candidate.score = normalized
    candidate.reasons = reasons or ["Selected as a well-paced, self-contained segment"]

    return candidate


def score_candidates(candidates: list, top_n: int = TOP_SCENES_COUNT, ideal_length: float = None, max_length: float = None) -> list:
    """Scores every candidate, sorts best-first, returns the top N."""
    scored = [_score_one(c, ideal_length=ideal_length, max_length=max_length) for c in candidates]
    scored.sort(key=lambda c: c.score, reverse=True)

    # de-duplicate heavily overlapping windows -- keep the higher scorer
    final = []
    for c in scored:
        overlaps_kept = any(
            not (c.end <= kept.start or c.start >= kept.end)
            for kept in final
        )
        if not overlaps_kept:
            final.append(c)
        if len(final) >= top_n:
            break

    return final
