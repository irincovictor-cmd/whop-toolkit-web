# Review & Roadmap

**Last updated:** 2026-08-20  
**Purpose:** Single source of truth for current project status, known bugs, product requirements, and prioritized fixes. Any AI or developer should read this before changing code so prompts stay short.

Related docs:
- `docs/MIGRATION_PLAN.md` — why frontend/backend are split, module mapping from the CLI
- `docs/DIRECTORY_STRUCTURE.md` — folder layout
- `docs/legacy_cli_docs/` — original CLI (archived, not runtime)
- Figma prototype: [Whop Toolkit — UI Prototype](https://www.figma.com/design/NNmXpsosmbC3fPIZICfZOs)

---

## Project summary

Whop Toolkit Web is a migration of a Python CLI into:

| Layer | Stack | Role |
|--------|--------|------|
| **Frontend** | Next.js 15 (App Router) + Tailwind | UI, Whop OAuth (PKCE), proxies to backend, Gemini analysis |
| **Backend** | FastAPI + Docker | yt-dlp, ffmpeg, faster-whisper (must not run in serverless) |

Core flows (local dev today):
1. Paste video URL → metadata (`GET /metadata`)
2. Extract clip by timestamps (`POST /clips/extract`)
3. Transcript (YouTube captions → Whisper fallback)
4. Gemini virality / summary analysis (`POST /api/ai/analyze`)

Architecture decision is intentional: Next.js never runs yt-dlp/ffmpeg/Whisper. See `MIGRATION_PLAN.md` §2.

---

## Product requirements (sources & export)

These are **intended product behavior**. Implementation may lag; treat gaps as roadmap work, not accidental omissions.

### Supported sources (multi-platform)

Goal: accept links the way tools like SnapTik do for short-form platforms — not YouTube-only.

| Platform | Status in code today | Target |
|----------|----------------------|--------|
| YouTube | Supported (`detect_platform` + extractors) | Keep |
| TikTok | Detected; download quality depends on yt-dlp | Full + clip flows |
| Instagram | Detected | Full + clip flows |
| X / Twitter | Detected | Full + clip flows |
| Vimeo | Detected | Full + clip flows |
| **Facebook** | **Not in `detect_platform` yet** | Add detection + test extractors |
| Other yt-dlp sites | Falls through as `generic` | Best-effort |

**Full video download (SnapTik-style):** product intent is to support downloading the best available stream for supported platforms, preferring versions **without platform watermarks** when yt-dlp exposes them.

**Honest limits (document in UI/help, do not over-promise):**
- Watermark-free output is **best-effort**. Platforms change CDN/API behavior; yt-dlp extractors break and get fixed upstream.
- Some sources only offer watermarked or lower-quality public streams.
- Private / login-gated / region-blocked videos are out of scope unless cookies/auth is explicitly added later.
- Keep yt-dlp updated in the Docker image; pin or document version in deploy notes.

**Code touchpoints:**
- `backend/app/core/ytdlp_client.py` — `detect_platform` / `build_ydl_options` (add `facebook.com` / `fb.watch`)
- `backend/app/routes/clips.py` — section download + format selection
- Future: optional “full download” route (not only timestamp crop) if product needs whole-file export without timestamps

### Export options (clip / convert)

Users must be able to choose **how** the output is framed and encoded — not only container type.

| Control | Options | Notes |
|---------|---------|--------|
| **Container** | `mp4`, `mp3`, `wav` | Already partially in UI |
| **Aspect** | `original`, `portrait` (9:16), `landscape` (16:9) | For Shorts / Reels / TikTok vs horizontal |
| **Fit mode** | `letterbox` (pad with bars), `cover` (scale/zoom to fill) | **Never default to center-crop that slices faces off the sides without the user choosing Cover** |
| **Resolution cap** | `720`, `1080`, `source` | Caps output height; does not “upscale magic” beyond source |
| **Max file size** (optional) | e.g. target MB | Legacy CLI had this; re-encode to fit when set |

**Portrait / Cover rule (product decision):**
When the user picks **Portrait 9:16** + **Cover**, scale the frame so the target aspect is filled (zoom/stretch-to-fill behavior agreed with the team) — **do not** only crop equal strips from left/right in a way that feels like the video was “sliced.” Letterbox remains available when the user wants the full frame visible with bars.

**Implementation status:**
- **Web UI today:** only format `mp4|mp3|wav`; no aspect / fit / resolution pickers.
- **Backend clips route today:** hardcodes `bestvideo[height<=1080]+bestaudio/best` — no user-driven aspect/fit.
- **Legacy CLI:** vertical 9:16 letterbox vs landscape; optional MB cap — reference in `docs/legacy_cli_docs/USER_GUIDE.md` Option 3.
- **Figma:** Extract panel should show Aspect, Fit, Quality (see prototype).

**Backend direction (when implementing):**
- Accept `aspect`, `fit`, `height` (or `quality`), optional `max_mb` on clip/convert requests.
- Apply ffmpeg scale/pad (letterbox) or scale/crop (cover) as fixed recipes — still **no free-form ffmpeg from the client**.
- yt-dlp format string should respect height cap (`<=720` / `<=1080` / best).

---

## What’s already good (do not undo)

- Separate deployable frontend vs backend container
- Stream-crop via `yt-dlp --download-sections` (avoid full video download when clipping)
- Whop OAuth + PKCE with httpOnly cookies; `DEV_SKIP_AUTH` for local UI
- Gemini key server-side only; structured JSON schema for analysis
- Convert route uses fixed ffmpeg recipes (no client-supplied ffmpeg args)
- Clip validators ported from CLI duration bounds
- Honest stubs documented in README (CORS, FileResponse, no DB, no rate limits)

---

## Known bugs (fix first)

### B1. Syntax / indentation error — `backend/app/routes/transcript.py`

Around the YouTube captions branch, indentation is broken so the route may fail to import:

```python
# BAD (current-style mis-indent observed)
info = get_metadata(req.url)

  if info.get("video_id") and ("youtube.com" in req.url or "youtu.be" in req.url):
        captions = _fetch_youtube_captions(info["video_id"])
```

**Fix:** Align the `if` with the rest of the function body; ensure the whole file is valid Python.

Also: calling `get_metadata` as a Python function from another route works only in-process. Prefer a small shared helper (e.g. extract metadata logic into `app/core/metadata_service.py`) instead of route-to-route function calls.

### B2. Temp directories leak on clip extraction — `backend/app/routes/clips.py`

`tempfile.mkdtemp` is never cleaned up after `FileResponse`. Transcript path cleans in `finally`; clips do not.

**Fix:** Clean work dir after response is sent (BackgroundTask), or always upload to object storage and delete local files. Until storage exists, at least `shutil.rmtree(work_dir, ignore_errors=True)` in a FastAPI `BackgroundTask` after the response.

### B3. Whisper model loaded every request — `backend/app/routes/transcript.py`

`WhisperModel(model_size, ...)` inside `_transcribe_with_whisper` is slow and memory-heavy.

**Fix:** Module-level or app-startup cache, e.g. dict keyed by model size, load once, reuse.

### B4. Path traversal risk — `backend/app/routes/convert.py`

`work_dir / file.filename` trusts the upload name.

**Fix:** Use a generated name (`uuid` + safe extension), never the raw client filename for the path.

### B5. CORS not actually driven by env — `backend/app/main.py`

Comment says lock via `FRONTEND_ORIGIN`; code hardcodes `allow_origins=["*"]`.

**Fix:**
```python
import os
origins = [o.strip() for o in os.getenv("FRONTEND_ORIGIN", "*").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, ...)
```

### B6. Backend has no auth of its own

Frontend checks Whop session, but FastAPI is open if reachable. Anyone with the backend URL can burn CPU/API.

**Fix:** Shared secret header, e.g. `X-Internal-Key` compared to `BACKEND_INTERNAL_KEY` env on both sides. Next.js proxies must send it; reject missing/wrong key with 401.

---

## Repo hygiene (do immediately)

### H1. No `.gitignore` (or incomplete)

Committed / should never be committed:
- `frontend/.next/`
- `backend/app/**/__pycache__/`
- `backend/.env`, `frontend/.env.local`
- `*.pyc`, `node_modules/`, `.DS_Store`

**Fix:** Add root `.gitignore` (see recommended content in this doc’s appendix or repo root). Remove tracked artifacts from the index (`git rm -r --cached ...`) without deleting local files. Env files should only exist as `.env.example`.

### H2. Placeholder env files tracked

`backend/.env` and `frontend/.env.local` currently mirror examples. Still remove from git so real secrets never get committed later.

---

## Production gaps (documented stubs)

These are intentional incomplete areas, not accidental oversights:

| Gap | Location | Required direction |
|-----|----------|--------------------|
| Clip delivery via local `FileResponse` | `backend/app/routes/clips.py` | Upload to S3-compatible storage; return signed URL |
| No rate limiting / quotas | Frontend API routes + backend | Per-user limits (Whop `sub`); cost control for Gemini + compute |
| No database | Entire stack | Postgres: `projects`, `activity_log` keyed by Whop `sub` + `(platform, video_id)` |
| Convert UI missing | Frontend | Backend `POST /convert` exists; no UI wired |
| **Export aspect / fit / quality UI + API** | Frontend + `clips.py` / convert | See **Product requirements** above |
| **Facebook in `detect_platform`** | `ytdlp_client.py` | Add hosts; test download |
| **Watermark-free full downloads** | Backend + docs | Best-effort via yt-dlp; UI disclaimer |
| Gemini suggestions lack timestamps | `api/ai/analyze` + UI | Return start/end hints so UI can one-click extract |
| Long jobs / timeouts | Proxies | Job queue or async jobs + polling; progress UX |
| No tests | — | Validators, auth helpers, route happy-paths |

---

## Priority order for implementers

**P0 — must fix before any shared deploy**
1. `.gitignore` + untrack `.next`, `__pycache__`, `.env*`
2. B1 transcript indentation / import
3. B5 CORS from `FRONTEND_ORIGIN`
4. B6 internal API key between Next and FastAPI

**P1 — reliability / security**
5. B2 temp cleanup on clips
6. B3 Whisper singleton/cache
7. B4 safe convert filenames
8. Structured logging on backend (stdout JSON or at least request path + duration)

**P2 — production clip path + export controls**
9. S3 (or R2/MinIO) upload + signed URL for clips
10. BackgroundTask cleanup after upload
11. **API + UI: aspect, fit (letterbox/cover), resolution cap, optional max MB**
12. **Facebook platform detection; document multi-platform + watermark best-effort**

**P3 — product completeness**
13. Postgres schema + project/activity APIs
14. Rate limits + basic quotas
15. Async jobs / progress for long extract & transcribe
16. Wire convert in UI; Gemini quote → timestamp → extract loop
17. Minimal tests

---

## Env vars checklist

**Frontend (`.env.local` / host dashboard)**
- `NEXT_PUBLIC_WHOP_APP_ID`
- `WHOP_CLIENT_SECRET`
- `WHOP_REDIRECT_URI`
- `BACKEND_SERVICE_URL`
- `GEMINI_API_KEY`
- `DEV_SKIP_AUTH` (local only; never `true` in production)
- `BACKEND_INTERNAL_KEY` (once B6 is implemented)

**Backend (`.env` / host dashboard)**
- `FRONTEND_ORIGIN` (comma-separated allowed origins in production)
- `PORT` (set by host)
- `BACKEND_INTERNAL_KEY` (once B6 is implemented)
- Optional later: `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_ENDPOINT`

---

## Coding conventions for this repo

- Do not run yt-dlp / ffmpeg / Whisper inside Next.js API routes.
- Prefer extending existing modules over rewriting working paths.
- Keep convert/scale recipes fixed allowlists (security) — letterbox vs cover are named modes, not arbitrary filters.
- Prefer signed URLs over streaming large files through serverless.
- Log to stdout in the backend (container-friendly), not local log files.
- When fixing a bug or shipping a product requirement in this list, update this file (mark done + date).

---

## Appendix: recommended root `.gitignore`

```
# Dependencies
node_modules/
frontend/node_modules/

# Next.js
frontend/.next/
frontend/out/

# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
backend/.venv/

# Env / secrets
.env
.env.*
!.env.example
!**/.env.example
frontend/.env.local
backend/.env

# OS / IDE
.DS_Store
.idea/
.vscode/
*.swp

# Logs / temp
*.log
tmp/
temp/
```

---

## How to use this doc with an AI

Short prompt template:

> Read `docs/REVIEW_AND_ROADMAP.md` and `docs/MIGRATION_PLAN.md`. Implement **P0** items (H1, B1, B5, B6). Do not expand scope into P2/P3 unless asked. Update `docs/REVIEW_AND_ROADMAP.md` to mark completed items.

For export UI/API work:

> Read **Product requirements (sources & export)** in `docs/REVIEW_AND_ROADMAP.md`. Implement aspect / fit / quality on clip extract end-to-end (validators → Next proxy → FastAPI → ffmpeg recipes). Portrait+Cover must scale-to-fill, not silent side-slice crop unless user chose Cover intentionally and UI labels it.
