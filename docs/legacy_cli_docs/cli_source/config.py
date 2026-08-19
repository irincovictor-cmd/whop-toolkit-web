"""
Global configuration for Whop Toolkit.

Only cross-project settings live here (paths that are shared,
download defaults, model choices). Per-video data always lives
inside that video's own project folder (see core/project.py).
"""

from pathlib import Path

# ==========================
# PATHS
# ==========================

# Root = the folder this file lives in, wherever the toolkit is installed.
# No hardcoded machine-specific paths.
ROOT = Path(__file__).resolve().parent

# Everything the app *generates* lives under one data/ folder, kept
# separate from the app's own code (core/, modules/, docs/, whop.py,
# config.py). Opening the project root should show "this is the app"
# at a glance, not a mix of code and output.
DATA_FOLDER = ROOT / "data"

# "projects" is the folder for all projects as a whole; each video gets
# its own subfolder underneath it (see core/project.py:VideoProject).
PROJECTS_FOLDER = DATA_FOLDER / "projects"
QUICK_CLIPS_FOLDER = DATA_FOLDER / "quick_clips"
CONVERTED_FOLDER = DATA_FOLDER / "converted_media"
CACHE_FOLDER = DATA_FOLDER / "cache"
LOGS_FOLDER = DATA_FOLDER / "logs"
MODELS_FOLDER = DATA_FOLDER / "models"

# Cache subfolders
AUDIO_CACHE_FOLDER = CACHE_FOLDER / "audio"
WHISPER_CACHE_FOLDER = CACHE_FOLDER / "whisper"

# Create shared folders automatically
for folder in [
    DATA_FOLDER,
    PROJECTS_FOLDER,
    QUICK_CLIPS_FOLDER,
    CONVERTED_FOLDER,
    CACHE_FOLDER,
    LOGS_FOLDER,
    MODELS_FOLDER,
    AUDIO_CACHE_FOLDER,
    WHISPER_CACHE_FOLDER,
]:
    folder.mkdir(parents=True, exist_ok=True)

# ==========================
# DOWNLOAD SETTINGS
# ==========================

DEFAULT_VIDEO_QUALITY = "1080"
PREFERRED_FORMAT = "mp4"

# ==========================
# CLIP SETTINGS
# ==========================

MIN_CLIP_LENGTH = 15   # seconds
MAX_CLIP_LENGTH = 90   # seconds
IDEAL_CLIP_LENGTH = 45  # seconds, used by the scorer for length scoring

# How many top candidates to show/export by default
MAX_CANDIDATES_TO_SHOW = 10

# ==========================
# TRANSCRIPT SETTINGS
# ==========================

# Order: try YouTube captions first, fall back to Whisper only if needed.
WHISPER_MODEL_SIZE = "base"     # tiny, base, small, medium, large-v3
WHISPER_DEVICE = "cpu"          # "cpu" or "cuda"
WHISPER_COMPUTE_TYPE = "int8"   # good default for CPU with faster-whisper

# ==========================
# SCORING WEIGHTS
# ==========================
# Used by modules/scorer.py. Values are relative weights, not percentages.

SCORE_WEIGHTS = {
    "hook": 1.4,
    "curiosity": 1.2,
    "emotion": 1.0,
    "story": 1.0,
    "length_fit": 0.8,
    "pause_boundary": 0.6,
}
