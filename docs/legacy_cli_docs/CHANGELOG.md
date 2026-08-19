# Changelog

## v0.4

Added
- Whisper fallback transcription (faster-whisper, base/small/medium)
- SRT subtitle export alongside plain-text transcripts
- Hallucination filtering for repeated Whisper output
- Top 5 scene detection (offline heuristic scorer, no API cost)
- scenes.json / scenes.txt caching per project
- Video cropper: cached-scene mode and manual-timestamp mode
- Aspect ratio (9:16 / 1:1 / original), resolution, quality preset,
  and target-file-size (bitrate-calculated) export options
- Storage Manager: Auto-Clean toggle, Clear Video Cache, Deep Clean
- Global activity_log.json with "Welcome back" session recap
- Global settings.json for cross-session preferences
- Full CLI menu loop in whop.py tying every module together
- docs/USER_GUIDE.md, DEVELOPER_GUIDE.md, SHARING_GUIDE.md

Fixed
- transcript.py referenced project.project_path, which didn't exist on
  VideoProject (it's project_folder) -- transcripts were silently never
  being saved. VideoProject now exposes both, and every path the app
  needs is a named attribute on the class.
- config.py had a hardcoded Windows-specific absolute path
  (C:\Users\Victorjames\...) as ROOT. Now derived from the toolkit's own
  file location, so it works on any machine/OS without editing.
- Source video downloads are now forced to .mp4 via yt-dlp's merge/convert
  settings for consistent editing-software compatibility.

## v0.1

Added
- Config
- Utils
- Project structure

Fixed
- Import issues

Improved
- Folder organization

## v0.5 (unreleased)

Added
- Support for local video files with no YouTube link: new "A file I
  already have" option in the Transcript menu, VideoProject.source_type,
  modules/metadata.py:fetch_local_metadata(), and
  modules/downloader.py:import_local_video() / extract_audio_from_source()
- Local uploads skip the YouTube-captions attempt entirely and go
  straight to Whisper transcription using the imported file's own audio
- Cropper, scorer, storage manager all work identically on local and
  YouTube-sourced projects with no source-specific branching needed

## v0.6 (unreleased)

Fixed
- download_source_video() was hitting "HTTP Error 403: Forbidden" from
  YouTube during the Video Cropper step. Added extractor_args to drop
  the failing android_sdkless client, a real browser User-Agent header,
  and rm_cachedir to avoid a stale cached signature causing repeat 403s.
  If a 403 still happens, the terminal now tells the user to run
  pip install -U --pre "yt-dlp[default]" for the latest hotfix.

## v0.7 (unreleased)

Changed -- major menu refactor
- Replaced the 4-option menu (Transcript / Top 5 Scene Detection / Video
  Cropper / Storage Manager) with a simplified 5-option menu focused on
  speed: Extract Transcript, Direct YouTube Video Clipper, Quick
  Stream-Crop, Clear Download Cache, Exit.
- NEW Direct YouTube Video Clipper (Option 2): paste a URL, enter
  duration-validated timestamps, crop straight from YouTube's CDN via
  downloader.get_stream_urls() + stream_crop_clip() -- no full video
  download. Output goes to the new quick_clips/ folder.
- NEW Quick Stream-Crop (Option 3): reuses the in-memory session video
  set by Option 1 if one exists this run, otherwise prompts for a local
  drag-and-drop file (auto-strips quote marks, validates the path
  exists). Works on both local files and a remembered YouTube URL.
- Vertical 9:16 export now letterboxes (scale + pad with black bars)
  instead of center-cropping, so faces/action are never cut off. No
  longer needs to ffprobe source dimensions -- uses ffmpeg's own
  runtime expressions, so it works on remote stream URLs too.
- Simplified the export prompt for the two new options to just
  Format (Vertical 9:16 / Landscape 16:9) + optional size cap, instead
  of the old three-question aspect/resolution/quality prompt.
- The old Top 5 Scene Detection and full Video Cropper flows are no
  longer reachable from the menu. Their modules (analyzer.py, scorer.py,
  exporter.py, core/candidate.py) were NOT deleted -- see
  docs/DEVELOPER_GUIDE.md for how to reattach them if needed.
- Storage Manager's Auto-Clean toggle and Deep Clean are likewise
  orphaned (core/settings.py, storage_manager.toggle_auto_clean(),
  storage_manager.deep_clean()) -- Clear Download Cache is the only
  storage action wired into the new menu.

Fixed
- HF_HUB_DISABLE_SYMLINKS=1 added alongside the existing warning
  suppression, at the absolute top of whop.py -- prevents WinError 1314
  crashes for standard (non-admin) Windows accounts during faster-whisper
  model downloads, which try to symlink into the HF cache by default.
- prompt_manual_timestamps() now validates against the video's actual
  duration when known, rejecting a start/end that would run past the end
  of the video instead of handing ffmpeg a nonsensical range.

## v0.8 (unreleased)

Changed
- Switched yt-dlp's player_client extractor_args to ['default', 'android']
  across every yt-dlp call site (metadata.py, download_source_video,
  download_audio_only, get_stream_urls) -- the android client's API layer
  avoids needing yt-dlp to solve YouTube's 'n' signature parameter with an
  external JS engine for most formats, reducing the "No supported
  JavaScript runtime" warning and the throttled-format fallback tied to it.
- download_audio_only() now strictly requests 'ba/ba*' (audio-only,
  falling back to best-available only if no pure audio stream exists) and
  extracts to mp3 @ 128kbps instead of bestaudio/best -> m4a. A captionless
  video's Whisper fallback now never risks pulling video data.
  VideoProject.source_audio_path changed from audio.m4a to audio.mp3 to match.
- Replaced silent/blocking subprocess.run(capture_output=True) calls with
  a live single-line progress bar for every yt-dlp download (via
  progress_hooks) and every ffmpeg operation (via streaming stderr parsing
  of ffmpeg's own time= stats) -- covers download_source_video,
  download_audio_only, import_local_video's mp4 conversion,
  extract_audio_from_source, crop_clip, and stream_crop_clip.

## v0.9 (unreleased)

Changed
- Replaced Option 4 (Clear Download Cache) with the Smart Media Converter:
  drag-and-drop or paste a local video/audio file, extension is
  auto-detected, and the matching conversion sub-menu is shown --
  5 video-target recipes (MP4/H.264, MKV copy, WebM/VP9, MP3 extract,
  WAV extract) and 3 audio-target recipes (MP3, AAC/M4A, WAV). New
  modules/converter.py, new config.CONVERTED_FOLDER. Output is always
  named <original>_converted.<ext>, never overwrites the source, and
  auto-appends a timestamp on the rare case that name is already taken.
- storage_manager.clear_video_cache() is no longer wired into the menu
  (same "orphaned, not deleted" treatment as the earlier Top 5 Scene
  Detection modules) -- see docs/DEVELOPER_GUIDE.md if reattaching it.

Fixed
- _run_ffmpeg_with_progress() was printing "100% -- done" even when
  ffmpeg's returncode indicated failure, which could look like a
  successful conversion/crop right before the error was raised. Now
  prints a "-- failed" status instead when returncode != 0.

## v0.10 (unreleased)

Added
- modules/utils.py:prompt_file_path() -- every "give me a local file"
  prompt (Option 1's local import, Option 3's fallback, Option 4's
  converter) now offers a native OS file-browser window as an
  alternative to typing/drag-and-dropping a path. Uses tkinter
  (ships with standard Python on Windows/Mac), with a clean fallback
  message if tkinter isn't available or no display window can open.

Fixed
- extract_audio_from_source() (used for local video uploads' Whisper
  fallback) was still encoding with the AAC codec while writing to
  project.source_audio_path, which became a .mp3-suffixed path in the
  v0.8 audio-only acceleration change -- codec/container mismatch
  caused every local-upload transcription to fail with "Invalid audio
  stream. Exactly one MP3 audio stream is required." Now encodes with
  libmp3lame to match the .mp3 extension it's actually writing to.

## v0.11 (unreleased)

Changed
- All generated content (projects/, quick_clips/, converted_media/,
  cache/, logs/, models/, activity_log.json, settings.json) now lives
  under a single data/ folder, separate from the app's own code
  (whop.py, config.py, core/, modules/, docs/). Project root is now
  code-only and much easier to scan in Explorer/Finder.
- .gitignore simplified to just data/ + __pycache__/ + *.pyc.
- No change to per-project layout: data/projects/ is still "the folder
  for all projects", each video still gets its own subfolder underneath
  it -- that part of the structure was already correct, just moved.

Migration note: if upgrading an existing install, move your existing
projects/, quick_clips/, converted_media/, cache/, logs/, models/,
activity_log.json, and settings.json into a new data/ folder before
running the updated whop.py. See docs/MIGRATING_TO_DATA_FOLDER.md.

## v0.12 (unreleased)

Fixed -- all Critical items from the code review
- Menu dispatch in whop.py's main() loop now wraps each action in its
  own try/except. Previously, any exception that wasn't a RuntimeError
  (missing dependency, unexpected API response, etc.) propagated all
  the way up and killed the entire session. Now it's logged, a friendly
  message is shown, and the app returns to the main menu.
- get_stream_urls() no longer risks an unhandled StopIteration when no
  matching video/audio format is found -- raises a clear RuntimeError
  instead.
- Added an ffmpeg-on-PATH check at startup, before the welcome message.
  Missing ffmpeg now prints a clear message pointing to the User Guide
  instead of crashing on first real use with a raw FileNotFoundError.
- crop_clip(), stream_crop_clip(), and converter.convert_file() now
  delete the output file if ffmpeg fails partway through, instead of
  leaving a corrupt, partially-written file that looks like a real
  output.

Changed -- project deduplication (core/project.py)
- Projects are now keyed by video_id instead of sanitized title.
  Title changes on YouTube's end (edits, whitespace, unicode
  normalization) no longer create a duplicate project folder for the
  same video.
- Added VideoProject.find_by_video_id(), used by Option 1's YouTube URL
  flow: pasting a URL for a video you already have a project for now
  offers "Continue with existing" or "Refresh metadata and continue"
  instead of silently creating a second folder.
- Added VideoProject.list_all_with_titles() for CLI pickers, since
  folder names are now IDs, not human-readable titles.
- Backwards compatible: existing projects created before this change
  (folder-named by title) are still found correctly by
  find_by_video_id(), since it matches on info.json's video_id field
  regardless of what the folder itself is named. No migration needed.

Changed -- multi-platform import groundwork (modules/metadata.py)
- Added detect_platform(url) and build_ydl_options(), a shared yt-dlp
  options builder used by every call site (metadata fetch, full
  download, audio-only download, stream URL resolution).
  YouTube-specific extractor_args (player_client) are now only applied
  for actual YouTube URLs; every other platform gets a generic
  User-Agent + Referer instead, which several sites (TikTok included)
  need to respond reliably. yt-dlp already auto-detects the platform
  itself for extraction -- this change just stops YouTube-only tuning
  from being sent to non-YouTube requests, and gives non-YouTube
  requests headers they're more likely to need.

## v0.13 (unreleased)

Fixed
- Investigated the reported "converted mp3 is shorter than the source
  video" issue. Reproduced it with a controlled test file and confirmed
  the ffmpeg extraction commands themselves are accurate -- they extract
  exactly what's in the source's audio stream. The actual cause is
  almost always that the source file's audio track was already shorter
  than its video track before conversion (common with merged
  adaptive-stream downloads, screen recordings, or phone video with
  encoder start delay) -- not data lost during conversion.
- converter.convert_file() now compares the source's probed duration
  against the actual output duration after any conversion. If they
  differ by more than 1 second, it prints a clear explanation instead
  of silently handing back a shorter file with no context. Small
  (<1s) differences from normal encoding rounding stay silent, as
  before.

## v0.14 (unreleased)

Investigated
- Reported bug: an MP4 clip (192.03s) converted to MP3 came out at
  100.10s -- a ~92s gap, far beyond normal stream-alignment variance.
  Systematically checked every hypothesis on the reporter's list:
    - No -ss/-to/-t/-shortest exist anywhere in the MP3-generating
      commands (_extract_mp3, _audio_to_mp3) -- confirmed by direct
      code inspection.
    - download_source_video() (the only true "full download" function)
      has zero callers anywhere in the current menu -- the MP4 in
      question must have come from stream_crop_clip() (Options 2/3),
      not a plain download.
    - No shared/reused start-end-duration variables between clip
      creation and Option 4's conversion -- confirmed by tracing
      menu_direct_clipper(), menu_quick_stream_crop(), and
      convert_file(): they don't share any state.
    - Built a real reproduction test simulating YouTube's separate
      video/audio DASH representations with mismatched internal
      timestamps, run through stream_crop_clip()'s actual dual -ss/-to
      command shape -- ffmpeg handled it correctly (92.0s out on both
      streams, no truncation). This was the leading hypothesis and it
      did not reproduce.
  Could not reproduce the exact 92s gap in a network-isolated sandbox;
  most likely explanation is real YouTube CDN/DASH-specific behavior
  for the specific video in question, not a logic bug in the reviewed
  code paths.

Added
- downloader._probe_stream_durations() and _check_clip_stream_mismatch():
  after every stream_crop_clip() and crop_clip() call, the finished
  clip's actual video-stream and audio-stream durations are compared
  against each other and against the requested duration. A >1s
  disagreement now prints and logs a diagnostic immediately, at
  clip-creation time, with the exact durations and source involved --
  instead of only being discoverable later if/when the clip happens to
  get converted to mp3.
