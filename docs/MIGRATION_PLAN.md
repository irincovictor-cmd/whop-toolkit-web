# Whop Toolkit: CLI → Web Migration Plan

## 1. Module Mapping

The CLI's module boundaries (see `docs/legacy_cli_docs/DEVELOPER_GUIDE.md` for the
original responsibility table) map cleanly onto the new architecture — this is
one of the few migrations where the existing separation of concerns was already
correct for a web split, so nothing needed to be redesigned, only relocated.

| CLI Module | Old Responsibility | New Home | Why |
|---|---|---|---|
| `modules/downloader.py` | yt-dlp downloads, ffmpeg crop/convert, all subprocess work | **Backend microservice** (`backend/`) | Needs a real filesystem, long-running processes, ffmpeg binary, and no serverless execution time limit. Never belongs in a Next.js API route. |
| `modules/transcript.py` | YouTube captions + faster-whisper fallback | **Backend microservice**, `POST /transcribe` | Whisper needs a persistent model cache and real compute — same constraint as downloader. |
| `modules/metadata.py` | yt-dlp metadata-only fetch, platform detection | **Backend microservice**, `GET /metadata` | Thin, fast, but still needs yt-dlp installed; keeping it server-side (not a Next.js route) avoids bundling yt-dlp into the frontend deploy. |
| `modules/scorer.py` + `modules/analyzer.py` | Offline heuristic clip ranking (legacy, unwired from the CLI menu) | **Replaced**, not migrated — becomes the Gemini AI route (`app/api/ai/analyze/route.ts`) | This is the intentional upgrade the spec calls for: swap the old heuristic scorer for real LLM-based virality scoring. The heuristic code stays archived in `docs/legacy_cli_docs/cli_source/` for reference, but nothing calls it going forward. |
| `modules/converter.py` | Format conversion (mp4/mkv/webm/mp3/wav) | **Backend microservice**, `POST /convert` | Same ffmpeg/filesystem constraint as downloader. |
| `modules/clip_selector.py` | CLI prompts (timestamps, format/size choices) | **Frontend** (Next.js forms/components) | This was always the CLI's *only* UI-layer module — it's the direct ancestor of the web UI's timestamp picker and export-options form. Its validation logic (duration bounds checking) should be ported as-is into a shared TypeScript validator, since the logic itself was already sound. |
| `core/project.py` | `VideoProject` — folder-per-project, video-ID-keyed dedup | **Backend microservice + database** | The dedup-by-video-ID logic (already fixed in v0.14) maps directly to a `projects` table keyed by `(platform, video_id)` with a unique constraint — same concept, different storage engine. |
| `core/activity_log.py` | Global session history, "welcome back" | **Database**, per-user, keyed by Whop `user.sub` | Was global/local before because the CLI had one user. On the web, this becomes genuinely per-user, which is a real upgrade the migration unlocks for free. |
| `core/logger.py` | File-based logging | **Backend microservice** structured logging (stdout, captured by Render/Railway) | Same purpose, different sink — containers should log to stdout, not a local file, so the platform's log aggregation picks it up. |
| `core/settings.py`, `modules/storage_manager.py` | Global settings, cache cleanup (legacy, unwired) | **Not migrated** | These were already unwired from the CLI menu in earlier iterations. No web equivalent needed yet — a hosted service doesn't have the same "clear my local disk cache" problem the CLI did. Archived for reference only. |
| `whop.py` | CLI menu loop, orchestration | **Split** across Next.js pages (UI orchestration) + backend route handlers (business-logic orchestration) | There's no single "main loop" equivalent on the web — this is expected; the CLI's menu *was* the UI layer, and the UI layer is now Next.js. |

## 2. Why a Separate Backend Microservice (Not All-in-Next.js)

This is the one architectural decision worth explaining before the directory
structure, since it's the difference between this working reliably and not:

- **Vercel/Cloudflare Pages serverless functions have execution time limits**
  (typically 10s–60s depending on plan) and no persistent filesystem. A
  multi-minute Whisper transcription or a multi-hundred-MB ffmpeg conversion
  will not survive in that environment.
- **yt-dlp and ffmpeg are native binaries.** They need a real container with
  those binaries installed — a Docker image on Render/Railway, not an edge
  function.
- **faster-whisper needs a persistent model cache directory** across requests,
  or every transcription re-downloads the model. A long-running container
  gives you that; a serverless function does not.

So: **Next.js never runs yt-dlp/ffmpeg/whisper directly.** It only ever calls
the backend microservice over HTTP and streams the result back to the browser.
This mirrors exactly how the CLI's `whop.py` never contained subprocess calls
itself — it always delegated to `modules/downloader.py`. Same principle, now
enforced by a process boundary instead of a Python import boundary.

## 3. Data Flow (Stream-Cropping, End to End)

```
Browser (React)
  │  POST /api/clips  { url, start, end, format }
  ▼
Next.js API route (app/api/clips/route.ts)
  │  validates Whop session (see auth section below)
  │  forwards to backend over internal network
  ▼
Backend microservice (FastAPI, Docker)
  │  yt-dlp --download-sections "*START-END" -f <fmt> --print-json (no full download)
  │  ffmpeg mux/transcode as needed
  │  uploads finished clip to object storage (S3-compatible), OR streams back directly
  ▼
Next.js API route
  │  returns { clipUrl } or streams the file
  ▼
Browser: download link / inline player
```

This preserves the CLI's core, deliberate optimization from `downloader.py`'s
`stream_crop_clip()` — never downloading the full source video, only the
requested timestamp range — it's just yt-dlp's `--download-sections` flag now
instead of the CLI's dual `-ss`/`-to`-before-`-i` ffmpeg approach, because on
the web, having yt-dlp do the range-limited fetch itself (rather than
resolving a raw CDN URL and streaming it through ffmpeg manually) is more
robust across the wider variety of source sites a public-facing tool will see.
