"""
Transcript acquisition: YouTube captions first, faster-whisper fallback.

Everything downstream works with classes.transcript_data.Transcript,
never with youtube_transcript_api or faster-whisper objects directly.
"""

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    CouldNotRetrieveTranscript,
)

import config
from core.logger import get_logger
from core.project import VideoProject
from classes.transcript_data import Transcript, TranscriptSegment

log = get_logger("transcript")

VALID_WHISPER_MODELS = ("base", "small", "medium")


# ==========================
# YOUTUBE CAPTIONS
# ==========================

def fetch_youtube_transcript(video_id: str) -> Transcript:
    """
    Tries to pull YouTube's own captions. Raises RuntimeError with a
    friendly message if none are available -- caller should fall
    back to Whisper.
    """
    try:
        raw = YouTubeTranscriptApi().fetch(video_id)
    except (TranscriptsDisabled, NoTranscriptFound, CouldNotRetrieveTranscript) as e:
        raise RuntimeError("No YouTube captions available for this video.") from e
    except Exception as e:
        log.warning(f"Unexpected error fetching YouTube transcript: {e}")
        raise RuntimeError("Could not reach YouTube for captions.") from e

    segments = [
        TranscriptSegment(
            start=float(line.start),
            end=float(line.start) + float(line.duration),
            text=line.text,
        )
        for line in raw
    ]
    return Transcript(language=getattr(raw, "language_code", "unknown"), source="youtube", segments=segments)


# ==========================
# WHISPER FALLBACK
# ==========================

def _filter_hallucinations(segments: list) -> list:
    """
    faster-whisper occasionally loops on silence/music and repeats the
    same phrase dozens of times. Drop runs of 3+ identical consecutive
    segments down to a single instance.
    """
    if not segments:
        return segments

    cleaned = [segments[0]]
    repeat_count = 1

    for seg in segments[1:]:
        prev_text = cleaned[-1].text.strip().lower()
        cur_text = seg.text.strip().lower()

        if cur_text and cur_text == prev_text:
            repeat_count += 1
            if repeat_count <= 2:
                cleaned.append(seg)
            else:
                # extend the previous segment's end time instead of
                # piling up duplicate lines
                cleaned[-1].end = seg.end
        else:
            repeat_count = 1
            cleaned.append(seg)

    return cleaned


def transcribe_with_whisper(audio_path, model_size: str = None, device: str = None) -> Transcript:
    """
    Runs faster-whisper locally on an audio/video file and returns a
    Transcript. Wrapped so a bad file, unsupported language, or model
    load failure never crashes the whole app.
    """
    model_size = model_size or config.WHISPER_MODEL_SIZE
    if model_size not in VALID_WHISPER_MODELS:
        log.warning(f"Unknown whisper model '{model_size}', defaulting to 'base'")
        model_size = "base"

    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise RuntimeError(
            "faster-whisper is not installed. Run: pip install faster-whisper"
        ) from e

    try:
        model = WhisperModel(
            model_size,
            device=device or config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE_TYPE,
            download_root=str(config.WHISPER_CACHE_FOLDER),
        )
        segments_iter, info = model.transcribe(str(audio_path), vad_filter=True)

        segments = [
            TranscriptSegment(start=float(s.start), end=float(s.end), text=s.text)
            for s in segments_iter
        ]
        segments = _filter_hallucinations(segments)

        if not segments:
            raise RuntimeError("Whisper produced an empty transcript for this file.")

        return Transcript(language=info.language or "unknown", source="whisper", segments=segments)

    except RuntimeError:
        raise
    except Exception as e:
        log.error(f"Whisper transcription failed: {e}")
        raise RuntimeError(f"Transcription failed: {e}") from e


# ==========================
# CACHING / ORCHESTRATION
# ==========================

def save_transcript(project: VideoProject, transcript: Transcript):
    """Saves transcript.json (cache), transcript.txt, and transcript.srt."""
    project.transcripts_folder.mkdir(exist_ok=True)
    transcript.save_json(project.transcript_json_path)
    transcript.save_txt(project.transcript_txt_path)
    transcript.save_srt(project.transcript_srt_path)
    return project.transcript_txt_path


def load_transcript(project: VideoProject) -> Transcript:
    return Transcript.load_json(project.transcript_json_path)


def get_transcript(project: VideoProject, model_size: str = None, force: bool = False) -> Transcript:
    """
    Master entry point. Order of operations:
      1. If already cached on disk, load it (unless force=True).
      2. Try YouTube captions.
      3. Fall back to downloading audio + faster-whisper.
    Always saves the result so step 1 short-circuits next time.
    """
    if not force and project.has_transcript():
        log.info(f"Using cached transcript for {project.title}")
        return load_transcript(project)

    if project.is_local:
        # No YouTube captions possible -- go straight to Whisper using
        # the already-imported local source video.
        from modules.downloader import extract_audio_from_source

        print("Local upload -- transcribing with Whisper...")
        audio_path = extract_audio_from_source(project)
        transcript = transcribe_with_whisper(audio_path, model_size=model_size)
        try:
            audio_path.unlink(missing_ok=True)
        except OSError:
            pass
    else:
        try:
            transcript = fetch_youtube_transcript(project.video_id)
            print("Found existing YouTube captions -- no transcription needed.")
        except RuntimeError as e:
            print(f"{e} Falling back to local Whisper transcription...")
            from modules.downloader import download_audio_only

            audio_path = download_audio_only(project)
            transcript = transcribe_with_whisper(audio_path, model_size=model_size)

            # audio was only needed for this step
            try:
                audio_path.unlink(missing_ok=True)
            except OSError:
                pass

    save_transcript(project, transcript)
    return transcript
