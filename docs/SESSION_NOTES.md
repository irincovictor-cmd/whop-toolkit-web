# Session notes (pinned handoff)

**Last updated:** 2026-08-24  
**Purpose:** Everything learned while bringing local web testing online and debugging YouTube quality. Read this + `REVIEW_AND_ROADMAP.md` before changing download/clip code.

Related:
- `docs/REVIEW_AND_ROADMAP.md` — bugs, priorities, product requirements
- `docs/legacy_cli_docs/cli_source/modules/downloader.py` — original CLI stream-crop
- Figma: https://www.figma.com/design/NNmXpsosmbC3fPIZICfZOs

---

## Documentation rule (standing)

**Every code or behavior change must be documented in this file in the same session as the push.**

Applies to Grok, Claude, and anyone else touching the repo.

| Change type | What to write |
|-------------|---------------|
| Bug fix | New **T#** test-log entry: where, symptom, cause, fix, verify, files |
| Behavior change (yt-dlp, formats, clients, timeouts) | Update **Current backend strategy** + test log if needed |
| New wiring (API route, UI↔backend) | Update **Frontend ↔ backend wiring** |
| Ops / run commands | Update **Local testing** or recovery checklist |
| Scope / priority shift | Update **Current focus** |

Also:
- Bump **Last updated** date
- Add a row to **Quick recovery checklist** when the symptom is user-visible
- Mention the fix under **Fixed in session** when relevant
- Do **not** ship code-only commits for behavioral changes without a docs update

Handoff: if you only pushed code, the next agent should treat missing docs as incomplete work.

**Coordination:** Grok (UI) and Claude (backend) must not overwrite each other’s format/cascade fixes without reading this file first. Audio probe (T11) and quality-first DASH strings (T13) both stay.

---

## What “done” looks like for product

- **Pass-through toolkit:** server fetches/processes briefly; user downloads to their device. **Not** a permanent media host.
- **Multi-platform:** YouTube, TikTok, Instagram, X, Vimeo; Facebook planned. Watermark-free = **best-effort** via yt-dlp.
- **Export controls (product):** aspect (original / 9:16 / 16:9), fit (letterbox / cover zoom-fill), quality cap, optional max MB. Portrait+Cover must not silent side-slice.

---

## Local testing (Windows — Victor’s machine)

| Item | Value |
|------|--------|
| Repo | `C:\Users\Victorjames\Documents\Codex\2026-08-23\are-you-codex\whop-toolkit-web` (also Desktop clone) |
| Clip output folder | `C:\Users\Victorjames\Desktop\whop clips` |
| Env | `LOCAL_OUTPUT_DIR` in `backend/.env` (see `.env.example`) |
| Auth skip | `DEV_SKIP_AUTH=true` in `frontend/.env.local` |
| Backend | **Must** `cd backend` then `uvicorn app.main:app --reload --port 8000` |
| Frontend | `cd frontend` → `npm run dev` → http://localhost:3000 |

There is **no** `docker compose up` yet. Two processes (or a local `start-dev.bat`).

**Common footgun:** running `uvicorn app.main:app` from the **repo root** → `ModuleNotFoundError: No module named 'app'`. Always run from `backend/`.

Successful clips/downloads are **also copied** into `LOCAL_OUTPUT_DIR` via `app/core/local_output.py`, and still streamed to the browser.

---

## Frontend ↔ backend wiring

### Connected

| Feature | Path |
|---------|------|
| Metadata | UI → `/api/metadata` → `GET /metadata` |
| Full download | UI → `/api/download` → `POST /download` |
| Clip extract | UI → `/api/clips` → `POST /clips/extract` |
| Transcript | UI → `/api/transcript` → `POST /transcript` |
| Local transcript | UI → `/api/transcript/local` → `POST /transcript/local` |
| Gemini | UI → `/api/ai/analyze` (Next.js only; not FastAPI) |
| Auth | Whop OAuth / `DEV_SKIP_AUTH` |

### UI only / not applied by backend yet

- Aspect, fit mode, quality picker, max MB (sent in JSON; **ignored** until export P2)
- Sidebar Projects / History / Settings (placeholders)

### Backend only / no UI

- `POST /convert` — exists; no Next proxy or UI

### Fixed in session (code)

- **B1** transcript.py IndentationError (import crash)
- Dark UI matching Figma (sidebar, extract panel, login)
- Facebook hosts in `detect_platform`
- Convert path uses uuid filename (B4 direction)
- YouTube client/format cascade (see below)
- **T11** Silent full-video downloads — audio probe + cascade (2026-08-24)
- **T13** 360p regression — DASH-only HQ/MID before progressive (2026-08-24)

---

## YouTube quality crisis (root cause — not “FastAPI broke UA”)

### Evidence from local CMD (same PC as the web backend)

1. `player_client=default,android` + DASH `401+251` → **403 mid-download** (SABR).
2. `player_client=android,web` + progressive (format **18**) → **100% success** (~126MB).
3. Incomplete URL `https://youtu.be` alone → homepage “recommended” playlist (operator error).
4. Some client sets report **DRM protected** when only DRM/SABR formats remain visible; other clients still get progressive.

### What is *not* the primary cause (when testing localhost)

- FastAPI async “changing headers” vs CLI (both shell out to yt-dlp on a home IP).
- Missing FFmpeg on PATH (failure was CDN 403 before a good merge).

### CLI vs web pipeline difference

| | Legacy CLI | Web backend |
|--|------------|-------------|
| Clip method | Resolve CDN URLs → ffmpeg `-ss` before `-i` | `yt-dlp --download-sections` |
| Clients | `default`, `android` | **`android`, `web`** + cascade |
| 9:16 | Letterbox filter in ffmpeg | UI only until P2 |

### Current backend strategy (`ytdlp_client` + download/clips)

**YouTube format attempts (in order) — do not collapse progressive into the HQ string:**

1. **HQ (DASH only):** `bestvideo[height<=1080]+bestaudio`
2. **MID (DASH only):** `bestvideo[height<=720]+bestaudio`
3. **SAFE (progressive):** `best[height<=1080][ext=mp4]/best[height<=720][ext=mp4]/…/best`

**Why DASH-only for HQ/MID:** If HQ is written as  
`bestvideo+bestaudio/best[height<=1080][ext=mp4]`, yt-dlp can pick **format 18 (360p)** inside the *first* attempt and exit 0 with audio — cascade never tries real 720/1080 DASH. That was **T13**.

Also:
- **On 403 / SABR / format not available:** clear partials, next attempt
- **On exit 0 but no audio** (ffprobe): clear partials, next attempt — **T11**
- Clients: `android,web`
- Optional `YTDLP_COOKIES`
- Timeout **600s**
- Keep yt-dlp updated: `pip install -U --pre "yt-dlp[default]"`

**Quality ceiling:** 1080p best-effort. Progressive fallback may be 720p or lower when DASH is blocked — better than silent or hard fail; do not market guaranteed 4K.

**Audio:** Full downloads must include an audio track (T11).

### PO tokens / proxies

- PO tokens: brittle; cascade first.
- Proxies: matter on cloud deploy IPs; not the local SABR issue.

---

## Test log / errors seen (Aug 2026 local session)

### T1 — Backend will not start (IndentationError)

**Cause:** Mis-indented `if` in `transcript.py`. **Fix:** Align indent. See earlier notes.

### T2–T10 — See git history / prior sections in older commits for full CMD transcripts (403, DRM, format 18 success, etc.).

### T11 — Full video download has no sound; clips from same URL have sound (2026-08-24)

**Cause:** HQ DASH could exit 0 with video-only; cascade only retried on 403.  
**Fix:** `probe_has_audio()`; retry next format if no audio.  
**File:** `backend/app/core/ytdlp_client.py`

### T12 — Uvicorn from repo root: No module named 'app'

**Fix:** `cd backend` before `uvicorn app.main:app --reload --port 8000`

### T13 — Full download stuck at 360p after silent-audio fix (2026-08-24)

**Where:** Dashboard full download after commit *Fix silent full-video downloads…*  
**Symptom:** User (and Claude quality work) expected highest available quality; got **360p** instead.

**Cause:** T11 patch changed `FORMAT_VIDEO_HQ` to include progressive fallbacks *inside the same `-f` string*:

```text
bestvideo[height<=1080]+bestaudio/best[height<=1080][ext=mp4]/best[height<=1080]
```

yt-dlp treats that as one selector. When DASH is awkward, it selects **format 18 (360p progressive)**, exits 0, audio probe passes → cascade stops. Quality work Claude/user did was effectively overridden.

**Fix (commit: Restore quality-first cascade…):**

```text
HQ  = bestvideo[height<=1080]+bestaudio     # DASH only
MID = bestvideo[height<=720]+bestaudio      # DASH only
SAFE = best[height<=1080][ext=mp4]/…/best   # progressive last
```

Keep **T11 audio probe**. Cascade on “format not available” as well as 403.

**Verify:** Re-download same YouTube URL; `ffprobe` height should be 720+ when DASH works, not stuck at 360. Label in filename / `X-Video-Quality` should match.

**File:** `backend/app/core/ytdlp_client.py`

---

### Quick recovery checklist

| Symptom | First check |
|---------|-------------|
| Uvicorn import crash / no module `app` | `cd backend`; T12 |
| 403 / ANDROID_VR / ffmpeg exit | Client + format cascade; update yt-dlp |
| DRM protected | `android,web`; other formats may still exist |
| Full download silent; clip has sound | **T11** audio probe |
| **Full download always 360p** | **T13** — HQ must be DASH-only; pull latest `ytdlp_client` |
| No file in `whop clips` | `LOCAL_OUTPUT_DIR`; only on success |

---

## Current focus (2026-08-24)

- **YouTube path solid** (audio + best practical quality) before other platforms or deploy.
- Smoke: metadata → full download (**with audio**, not stuck 360p when higher exists) → clip → transcript → analyze.

---

## Deploy & cost (short)

- Frontend free tiers OK for UI.
- Backend needs real CPU/RAM for yt-dlp + Whisper.
- Capacity = concurrent jobs, not registered user count.

---

## AI handoff prompt (copy-paste)

> Read `docs/SESSION_NOTES.md` and `docs/REVIEW_AND_ROADMAP.md`.  
> **Documentation rule:** every code/behavior change must update SESSION_NOTES in the same session.  
> YouTube cascade: **(1)** DASH 1080 `bestvideo+bestaudio` only, **(2)** DASH 720 only, **(3)** progressive SAFE. Never put `/best[ext=mp4]` inside the HQ string (T13 → 360p).  
> Also cascade when ffprobe finds **no audio** (T11). Clients: android+web.  
> Do not overwrite Claude/Grok format fixes without reading T11+T13.  
> Local output: `LOCAL_OUTPUT_DIR`. Export aspect/fit still P2.
