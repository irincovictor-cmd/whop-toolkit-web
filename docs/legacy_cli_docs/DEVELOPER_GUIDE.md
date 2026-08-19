# Whop Toolkit — Developer Guide

## Philosophy

CLI only, no database, no GUI. Every persistent thing is a file on disk.
Each module has exactly one job (see the table below) — if you're adding
a feature and can't tell which existing module it belongs in, it probably
needs a new module rather than being bolted onto an existing one.

## Module Responsibilities

| Module | Job | Never does |
|---|---|---|
| `core/project.py` | `VideoProject` — folder layout, path helpers, load/list/create | download, transcribe |
| `core/logger.py` | writes to `logs/whop.log` | print to console (that's the CLI's job) |
| `core/activity_log.py` | global `activity_log.json`, welcome-back message | per-project data |
| `classes/transcript_data.py` | `Transcript` / `TranscriptSegment` — the shared shape everything downstream uses | knows nothing about YouTube or Whisper |
| `modules/metadata.py` | `fetch_metadata(url)` / `fetch_local_metadata(path)`, no download | download the video |
| `modules/transcript.py` | orchestrates YouTube captions → Whisper fallback, caches result | cropping |
| `modules/downloader.py` | yt-dlp downloads, direct-stream cropping, all ffmpeg logic, shared progress-bar runner | transcript logic |
| `modules/converter.py` | Option 4's format-conversion routing + ffmpeg recipes | downloads, transcripts, projects/ |
| `modules/storage_manager.py` | clears cached source videos (legacy, orphaned) | anything unrelated to disk space |
| `modules/clip_selector.py` | CLI prompts (timestamps, format/size) | filesystem writes, ffmpeg calls |
| `modules/utils.py` | small stateless helpers (timestamps, prompts, file I/O) | anything project-specific |
| `whop.py` | main menu loop, in-memory session tracking, wires modules together | business logic — it should stay thin |

**Legacy, not wired into the current menu:** `core/candidate.py`
(`CandidateClip`), `modules/analyzer.py` (scene windowing), and
`modules/scorer.py` (heuristic Top-5 ranking) still exist and still work
-- they were the old "Top 5 Best Scene Detection" feature. `core/settings.py`
and `modules/storage_manager.py` (`clear_video_cache()`, `toggle_auto_clean()`,
`deep_clean()`) are also orphaned -- Option 4 used to be "Clear Download
Cache" and called these directly; it's now the Smart Media Converter
instead. None of this was deleted, since the logic is sound and might get
reattached to a menu option later. If you're picking this back up:
`analyzer.find_candidate_scenes(transcript)` → `scorer.score_candidates(candidates)`
is still a complete, working pipeline, just currently orphaned, and
`storage_manager.clear_video_cache()` still works exactly as documented
in earlier versions of this guide.

## Data Flow

**Option 1 — Extract Transcript** (the only flow that creates a full
project folder):

```
URL or local file path
 │
 ▼
metadata.fetch_metadata() / fetch_local_metadata()
 │
 ▼
VideoProject.create() + save_info()
 │
 ▼
(local file) downloader.import_local_video() ──► source.mp4 copied in
 │
 ▼
transcript.get_transcript()
   1. cache check (project.has_transcript())
   2. YouTube project: try YouTube captions, else downloader.download_audio_only()
      Local project: skip straight to downloader.extract_audio_from_source()
   3. transcribe_with_whisper() on whichever audio was obtained
   → Transcript saved via transcript.save_transcript()
 │
 ▼
whop.py stores {source_type, url/path, duration, title} in the in-memory
_session_video dict -- this is what lets Option 3 skip re-asking for the video.
```

**Option 2 — Direct YouTube Video Clipper** (bypasses projects/ entirely):

```
URL
 │
 ▼
metadata.fetch_metadata() ──► duration, for timestamp validation
 │
 ▼
clip_selector.prompt_manual_timestamps(duration) ──► validated start/end
 │
 ▼
clip_selector.prompt_format_and_size() ──► aspect_ratio / target_size_mb
 │
 ▼
downloader.stream_crop_clip(url, ...)
   1. get_stream_urls() ──► yt-dlp extract_info(download=False), no download
   2. ffmpeg with -ss/-to placed BEFORE each -i (range-request seek,
      not a full download) on the video-only and audio-only CDN URLs
   3. muxes both into quick_clips/<title>_<timestamp>.mp4
```

**Option 3 — Quick Stream-Crop**:

```
whop._session_video set by Option 1 this run?
   YES ──► reuse {source_type, url/path, duration} directly
   NO  ──► prompt for a local path, strip quote marks, os.path.exists() check,
           metadata.fetch_local_metadata() for duration
 │
 ▼
clip_selector.prompt_manual_timestamps(duration) + prompt_format_and_size()
 │
 ▼
source_type == "local" ──► downloader.crop_clip(local file path)
source_type == "youtube" ──► downloader.stream_crop_clip(url)
 │
 ▼
quick_clips/<title>_<timestamp>.mp4
```

**Option 4 — Smart Media Converter** (also bypasses `projects/` entirely):

```
local file path (drag-and-drop or pasted, quote-stripped, os.path.exists() checked)
 │
 ▼
converter.detect_media_type(path) ──► "video" / "audio" / None (extension lookup)
 │
 ▼
routes to VIDEO_MENU or AUDIO_MENU (a (label, output_ext, ffmpeg_builder) table --
whop.py's menu just displays labels and looks up the matching row, no
conversion logic lives in the CLI layer itself)
 │
 ▼
converter.convert_file() ──► builder(input, output) constructs the ffmpeg
   argv, _probe_duration() feeds the shared progress bar, output name is
   always <stem>_converted<ext> (timestamp-suffixed instead if that name's
   already taken) so the source file can never be overwritten
 │
 ▼
converted_media/<name>_converted.<ext>
```

`storage_manager.clear_video_cache()` (scans `projects/*/source.mp4` and
deletes them, leaving transcripts untouched) still works if called
directly, but as of the Smart Media Converter replacing Option 4, there's
currently no menu entry that calls it -- see the orphaned-modules note
above if you want to bring cache-clearing back as its own option.

## Local File Uploads (no URL)

`VideoProject.source_type` is `"youtube"` or `"local"`. For local uploads:

- `modules/metadata.py`'s `fetch_local_metadata(path)` reads duration via
  `ffprobe` and uses the filename as the title. `video_id` is a short hash
  of the file's absolute path, so re-importing the same file reuses the
  same project instead of duplicating it.
- `modules/downloader.py`'s `import_local_video()` **copies** (not moves)
  the file into `project.source_video_path` -- converting to mp4 first if
  needed. Because it's a copy, the user's original file is never touched,
  so even a stray `storage_manager.clear_video_cache()` call can't cause
  data loss; they can just re-import.
- `modules/transcript.py`'s `get_transcript()` checks `project.is_local`
  and skips the YouTube-captions attempt entirely, going straight to
  `downloader.extract_audio_from_source()` (ffmpeg, pulls audio out of
  the already-imported `source.mp4`) → Whisper.
- Option 3's Quick Stream-Crop branches the same way: `source_type ==
  "local"` uses `downloader.crop_clip()` on the file directly;
  `source_type == "youtube"` uses `downloader.stream_crop_clip()` on the
  URL. Neither path ever creates or depends on a full project folder.

## Caching / File-Checking Logic

Every expensive step checks for its own output before running:

- `VideoProject.has_transcript()` → Option 1 skips re-fetching/re-transcribing
  unless the user explicitly asks to re-run it.
- `VideoProject.has_source_video()` → `import_local_video()` no-ops if
  `source.mp4` already exists (re-picking the same local file twice in
  one session is free).

This is why `VideoProject` centralizes every path as an attribute
(`transcript_json_path`, `source_video_path`, etc.) — any module that
needs to check "does this already exist" imports `VideoProject`, never
hardcodes a path string itself.

Options 2 and 3's `quick_clips/` output has no caching layer by design
-- they're meant to be fast, disposable, one-off crops, not part of a
video's persistent project.

## Global vs Per-Project State

Two kinds of persistent data:

1. **Per-project** — lives inside `projects/<title>/`. Managed entirely by
   `VideoProject`. Only created by Option 1.
2. **Global** — `activity_log.json` (session history), at the project
   root, managed by `core/activity_log.py`. Decoupled from `VideoProject`
   on purpose, so clearing a project's cache never touches your history.
3. **In-memory only** — `whop._session_video`, set by Option 1, read by
   Option 3. Lives only for the current run of `whop.py`; restarting the
   program clears it (Option 3 will ask for a file again).

`core/settings.py` and `storage_manager.toggle_auto_clean()` /
`deep_clean()` still exist and work, but like the scene-ranking modules
above, they're currently orphaned -- the simplified 5-option menu doesn't
call them. They were built for the earlier Storage Manager submenu.

## Logging vs Console Output

`print()` is for the user-facing CLI flow (what they typed, what happened).
`core/logger.py`'s `get_logger(name)` is for the debug trail that survives
in `logs/whop.log` — stack traces, ffmpeg's raw stderr, anything a user
would report in a bug but doesn't need to see live. `whop.py`'s top-level
`except Exception` always logs the full traceback before printing a short
friendly message.

## Scoring Logic (modules/scorer.py) -- legacy, not in the current menu

Fully offline, rule-based, no API keys or cost. Each candidate gets
sub-scores for hook phrasing, curiosity gaps, emotional language, story
structure, and how close its length is to a target ideal length.
Sub-scores are weighted (`config.SCORE_WEIGHTS`) and normalized to a 0–10
scale. `find_candidate_scenes()` and `score_candidates()` both accept
`min_length`/`max_length`/`ideal_length` overrides (not just
`config.py` globals) specifically so a reattached menu option could let
the user pick a target clip length range and have it actually constrain
the parsing loop, not just the scoring afterward.

## Adding a New Menu Option

1. Write the logic in its own `modules/<name>.py` — one job, same rules
   as the table above.
2. Add a `menu_<name>()` function in `whop.py` that just calls into that
   module and handles the CLI back-and-forth.
3. Add it to the `ask_choice()` list in `main()`.
4. Log the completed action with `activity_log.log_activity(...)` so it
   shows up in the next session's welcome message.

## Testing Without Network Access

`yt-dlp`, `youtube_transcript_api`, and `faster_whisper` all require
network/model downloads. When testing offline, stub them at the package
level (see how this was verified during development — a `sys.path`
override with minimal fake `YoutubeDL`/`WhisperModel` classes is enough
to exercise every module's import graph and logic that doesn't need real
data). Anything touching real video/audio content should still be tested
against a real file before shipping — `ffmpeg`'s crop/scale/bitrate flags
in `downloader.py` were verified against a generated test clip.
