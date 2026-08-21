# Session notes (pinned handoff)

**Last updated:** 2026-08-21  
**Purpose:** Everything learned while bringing local web testing online and debugging YouTube quality. Read this + `REVIEW_AND_ROADMAP.md` before changing download/clip code.

Related:
- `docs/REVIEW_AND_ROADMAP.md` — bugs, priorities, product requirements
- `docs/legacy_cli_docs/cli_source/modules/downloader.py` — original CLI stream-crop
- Figma: https://www.figma.com/design/NNmXpsosmbC3fPIZICfZOs

---

## What “done” looks like for product

- **Pass-through toolkit:** server fetches/processes briefly; user downloads to their device. **Not** a permanent media host.
- **Multi-platform:** YouTube, TikTok, Instagram, X, Vimeo; Facebook planned. Watermark-free = **best-effort** via yt-dlp.
- **Export controls (product):** aspect (original / 9:16 / 16:9), fit (letterbox / cover zoom-fill), quality cap, optional max MB. Portrait+Cover must not silent side-slice.

---

## Local testing (Windows — Victor’s machine)

| Item | Value |
|------|--------|
| Repo | `C:\Users\Victorjames\Desktop\whop-toolkit-web` |
| Clip output folder | `C:\Users\Victorjames\Desktop\whop clips` |
| Env | `LOCAL_OUTPUT_DIR` in `backend/.env` (see `.env.example`) |
| Auth skip | `DEV_SKIP_AUTH=true` in `frontend/.env.local` |
| Backend | `uvicorn app.main:app --reload --port 8000` |
| Frontend | `npm run dev` → http://localhost:3000 |

There is **no** `docker compose up` yet. Two processes (or a local `start-dev.bat`).

Successful clips are **also copied** into `LOCAL_OUTPUT_DIR` via `app/core/local_output.py`, and still streamed to the browser.

---

## Frontend ↔ backend wiring

### Connected

| Feature | Path |
|---------|------|
| Metadata | UI → `/api/metadata` → `GET /metadata` |
| Clip extract | UI → `/api/clips` → `POST /clips/extract` |
| Transcript | UI → `/api/transcript` → `POST /transcript` |
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
| Clients (old) | `default`, `android` | Now `android`, `web` + cascade |
| 9:16 | Letterbox filter in ffmpeg | UI only until P2 |

### Current backend strategy (`ytdlp_client` + `clips.py`)

1. **Try HQ:** `bestvideo[height<=1080]+bestaudio/...`
2. **On 403 / SABR / forbidden-like stderr:** clear partials, **retry progressive-safe** formats.
3. Optional `YTDLP_COOKIES=/path/to/cookies.txt` for tougher sessions.
4. Keep yt-dlp updated: `pip install -U --pre "yt-dlp[default]"`.
5. Optional: Node.js/LTS for yt-dlp EJS / n-challenge solver (more formats).

**Quality ceiling:** 1080p is **best-effort**. When YouTube blocks DASH, users get lower progressive quality rather than a hard fail. Do not market guaranteed 4K.

### PO tokens / proxies

- PO tokens: real for some web/mweb GVS flows; brittle; cascade first.
- Proxies: matter on **cloud** deploy IPs; not the local SABR issue.

---

## Deploy & cost (short)

- Frontend free tiers (Vercel/Pages) OK for UI.
- Backend (yt-dlp + ffmpeg + Whisper) needs a **real** always-on box eventually; free tiers sleep/throttle.
- Gemini free tier is for demos; production needs billing + per-user limits.
- Capacity is limited by **concurrent extract/transcribe jobs**, not registered Whop users.

---

## AI handoff prompt (copy-paste)

> Read `docs/SESSION_NOTES.md` and `docs/REVIEW_AND_ROADMAP.md`.  
> YouTube: use quality cascade (HQ DASH → progressive on 403); clients android+web.  
> Local output: respect `LOCAL_OUTPUT_DIR`.  
> Export aspect/fit/quality are UI-ready but backend must apply ffmpeg recipes (P2).  
> Do not claim FastAPI UA as root cause of 403 on localhost. Update these docs when you change download behavior.
