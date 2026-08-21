# Review & Roadmap

**Last updated:** 2026-08-21  
**Purpose:** Single source of truth for current project status, known bugs, product requirements, and prioritized fixes. Any AI or developer should read this before changing code so prompts stay short.

**Also read:** `docs/SESSION_NOTES.md` — pinned learnings from local testing + YouTube SABR/quality work (Aug 2026).

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
2. Extract clip by timestamps (`POST /clips/extract`) — with YouTube **HQ→safe format cascade**
3. Transcript (YouTube captions → Whisper fallback)
4. Gemini virality / summary analysis (`POST /api/ai/analyze` on Next.js)

Architecture decision is intentional: Next.js never runs yt-dlp/ffmpeg/Whisper. See `MIGRATION_PLAN.md` §2.

**Product model:** fetch → process → **user downloads** (not a permanent video host). Optional `LOCAL_OUTPUT_DIR` copies finished files on disk for local testing.

---

## Product requirements (sources & export)

### Supported sources (multi-platform)

| Platform | Status in code today | Target |
|----------|----------------------|--------|
| YouTube | Supported; quality cascade for SABR/403 | Keep improving clients/formats |
| TikTok | Detected | Full + clip flows |
| Instagram | Detected | Full + clip flows |
| X / Twitter | Detected | Full + clip flows |
| Vimeo | Detected | Full + clip flows |
| Facebook | Hosts in `detect_platform` (`facebook.com`, `fb.watch`) | Test extractors in practice |
| Other yt-dlp sites | `generic` | Best-effort |

Watermark-free / SnapTik-style full download: **best-effort** only. Document limits in UI.

### Export options

| Control | Options | Status |
|---------|---------|--------|
| Container | mp4, mp3, wav | UI + backend |
| Aspect | original, portrait 9:16, landscape 16:9 | **UI only** — backend ignores |
| Fit | letterbox, cover (zoom fill) | **UI only** — backend ignores |
| Quality cap | 720 / 1080 / source | **UI only**; backend uses cascade formats |
| Max MB | optional | **UI only** |

Portrait + Cover = scale-to-fill (team decision); letterbox keeps full frame with bars. CLI reference: letterbox for 9:16 in legacy `downloader.py`.

---

## Frontend ↔ API matrix

| Feature | Wired? |
|---------|--------|
| Metadata / clips / transcript | Yes |
| Gemini analyze | Yes (Next only) |
| Aspect / fit / max MB | UI → JSON only |
| Convert | Backend only |
| Projects / History / Settings nav | Placeholders |

---

## What’s already good (do not undo)

- Separate frontend vs backend container
- Stream sections via yt-dlp (avoid full download when clipping)
- YouTube **format cascade** (try DASH HQ, fall back progressive on 403)
- `LOCAL_OUTPUT_DIR` helper for local disk copies
- Dark UI aligned with Figma prototype
- Whop OAuth + PKCE; `DEV_SKIP_AUTH` for local
- Gemini server-side only
- Convert recipes fixed allowlist

---

## Known bugs / status

| ID | Item | Status |
|----|------|--------|
| B1 | transcript.py IndentationError | **Fixed** (2026-08-20) |
| B2 | Clip temp dir leak | Open |
| B3 | Whisper reload every request | Open |
| B4 | Convert path traversal | **Mitigated** (uuid filename) — verify |
| B5 | CORS still `*` | Open |
| B6 | No backend internal key | Open |

---

## Repo hygiene

- Root `.gitignore` should exclude `.next`, `__pycache__`, `.env*`, `node_modules`
- Do not commit real secrets or cookies.txt

---

## Production gaps

| Gap | Direction |
|-----|-----------|
| FileResponse only | S3/R2 + signed URL |
| No rate limits | Per Whop user |
| No DB | projects / activity |
| Convert UI | Wire `/api/convert` + UI |
| Export ffmpeg recipes | aspect/fit/quality/max_mb |
| Gemini → timestamps | one-click extract |
| Long jobs | queue + progress |
| YouTube max quality | cascade + yt-dlp updates + optional cookies/EJS |

---

## Priority order

**P0 — before shared deploy**  
1. Hygiene: gitignore / untrack secrets artifacts  
2. B5 CORS from `FRONTEND_ORIGIN`  
3. B6 internal API key  

**P1 — reliability**  
4. B2 temp cleanup  
5. B3 Whisper cache  
6. Logging  

**P2 — clip product**  
7. S3 + cleanup  
8. **Export aspect/fit/quality/max_mb end-to-end**  
9. Optional cookies path documented for ops  

**P3 — completeness**  
10. DB / projects  
11. Rate limits  
12. Async jobs  
13. Convert UI + Gemini timestamps  
14. Tests  

---

## Env vars

**Frontend `.env.local`**  
`NEXT_PUBLIC_WHOP_APP_ID`, `WHOP_CLIENT_SECRET`, `WHOP_REDIRECT_URI`, `BACKEND_SERVICE_URL`, `GEMINI_API_KEY`, `DEV_SKIP_AUTH`, later `BACKEND_INTERNAL_KEY`

**Backend `.env`**  
`FRONTEND_ORIGIN`, `PORT`, `LOCAL_OUTPUT_DIR` (local), optional `YTDLP_COOKIES`, later `BACKEND_INTERNAL_KEY`, S3_*

Example local output (Windows):
```env
LOCAL_OUTPUT_DIR=C:\Users\Victorjames\Desktop\whop clips
```

---

## Coding conventions

- No yt-dlp/ffmpeg/Whisper inside Next.js routes
- YouTube: prefer cascade over hard-fail; do not assume FastAPI caused 403 on localhost
- Fixed ffmpeg recipes only (named aspect/fit modes)
- Update this file + `SESSION_NOTES.md` when download behavior changes

---

## How to use with an AI

> Read `docs/SESSION_NOTES.md` and `docs/REVIEW_AND_ROADMAP.md`. Implement the requested priority only. Mark completed items with date.
