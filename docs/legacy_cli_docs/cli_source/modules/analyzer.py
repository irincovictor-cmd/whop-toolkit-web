"""
Analyzer: turns a Transcript into candidate scene windows.

This module ONLY segments the transcript into time windows that are
worth scoring -- it does not judge quality. That's scorer.py's job.
"""

import config
from classes.transcript_data import Transcript
from core.candidate import CandidateClip

# Gaps between segments bigger than this suggest a natural topic
# break -- a good place to start or end a scene.
PAUSE_THRESHOLD_SECONDS = 1.2


def find_candidate_scenes(transcript: Transcript, min_length: float = None, max_length: float = None) -> list:
    """
    Slides a window across the transcript's segments, snapping window
    boundaries to natural pauses where possible, staying within
    [min_length, max_length] seconds. Falls back to config's
    MIN_CLIP_LENGTH/MAX_CLIP_LENGTH when not given explicitly, but Menu
    Option 2's length selector passes its own range so short/medium/long
    (or a custom range) actually constrains what gets found -- not just
    what gets scored afterward.
    """
    min_length = min_length or config.MIN_CLIP_LENGTH
    max_length = max_length or config.MAX_CLIP_LENGTH

    segments = transcript.segments
    if not segments:
        return []

    candidates = []
    n = len(segments)
    i = 0

    while i < n:
        window_start_idx = i
        window_start_time = segments[i].start
        j = i

        # grow the window until we hit max length or run out of segments
        while j < n and (segments[j].end - window_start_time) <= max_length:
            j += 1
        j = max(j - 1, window_start_idx)  # last included index

        # make sure we meet the minimum length; if not, extend forward
        while (
            j < n - 1
            and (segments[j].end - window_start_time) < min_length
        ):
            j += 1

        window_end_time = segments[j].end
        text = " ".join(s.text.strip() for s in segments[window_start_idx:j + 1])

        if (window_end_time - window_start_time) >= min_length:
            candidates.append(CandidateClip(
                start=round(window_start_time, 2),
                end=round(window_end_time, 2),
                text=text,
            ))

        # advance the window start to the next natural pause after
        # window_start_idx, so windows overlap and slide smoothly
        next_i = window_start_idx + 1
        for k in range(window_start_idx, j):
            gap = segments[k + 1].start - segments[k].end
            if gap >= PAUSE_THRESHOLD_SECONDS:
                next_i = k + 1
                break
        i = next_i if next_i > i else i + 1

    return candidates
