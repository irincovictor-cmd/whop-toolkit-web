# Session notes (pinned handoff)

**Last updated:** 2026-08-24  
**Purpose:** Everything learned while bringing local web testing online and debugging YouTube quality. Read this + `REVIEW_AND_ROADMAP.md` before changing download/clip code.

Related:
- **`docs/VIDEO_EXTRACTION_ARCHITECTURE.md`** — **production** direction: server-side yt-dlp deprecated; Options A/B/C
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
| Architecture / product direction | Update this file **and** the canonical doc (e.g. VIDEO_EXTRACTION_ARCHITECTURE) |

Also:
- Bump **Last updated** date
- Add a row to **Quick recovery checklist** when the symptom is user-visible
- Mention the fix under **Fixed in session** when relevant
- Do **not** ship code-only commits for behavioral changes without a docs update

Handoff: if you only pushed code, the next agent should treat missing docs as incomplete work.

**Coordination:** Grok (UI) and Claude (backend) must not overwrite each other’s format/cascade fixes without reading this file first. Audio probe (T11) and quality-first DASH strings (T13) both stay for **local/dev** yt-dlp.

---

## Production vs local (read this)

| Context | yt-dlp on server |
|---------|------------------|
| **Local dev / owner machine** | Allowed for YouTube-first hardening, demos, smoke tests |
| **Production / shared cloud backend** | **Deprecated** — see `docs/VIDEO_EXTRACTION_ARCHITECTURE.md` |

Do **not** design production features that assume stable multi-platform server-side yt-dlp (TikTok, IG, etc.). Prefer Option A (browser extension interception), B (managed extraction APIs), or C (Whop-native product surface).

---

## What “done” looks like for product

- **Pass-through toolkit:** process briefly; user keeps files on their device. **Not** a permanent media host.
- **Local/dev sources:** YouTube primary; others best-effort via yt-dlp where it still works.
- **Production extraction:** per VIDEO_EXTRACTION_ARCHITECTURE (not “scale the current FastAPI yt-dlp box”).
- **Export controls (product):** aspect / fit / quality in UI; backend application still roadmap P2.

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

**Common footgun:** uvicorn from repo root → `ModuleNotFoundError: No module named 'app'` (T12).

**Whisper first run:** faster-whisper downloads the model from Hugging Face; can take minutes. Empty/timeout responses → UI `Unexpected end of JSON input`. Wait for model cache under `%USERPROFILE%\.cache\huggingface\` then retry. HF symlink warning on Windows is harmless.

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

- Aspect, fit mode, quality picker, max MB (ignored until export P2)

### Fixed in session (code)

- T11 audio probe; T13 DASH-only HQ/MID; T12 uvicorn cwd; B1 transcript indent; quality labels; local Whisper path

---

## Current backend strategy (local yt-dlp only)

**YouTube format attempts:**

1. HQ: `bestvideo[height<=1080]+bestaudio` (DASH only)
2. MID: `bestvideo[height<=720]+bestaudio` (DASH only)
3. SAFE: progressive `best[height<=1080][ext=mp4]/…`

Never put progressive inside the HQ string (T13 → 360p). Cascade on 403/SABR and on missing audio (T11). Clients: `android,web`. Timeout 600s.

---

## Test log (abbreviated)

- **T11** Silent full download / clip OK → audio probe  
- **T12** No module `app` → `cd backend`  
- **T13** Stuck 360p → DASH-only HQ/MID  
- **T14** Local transcript `Unexpected end of JSON input` → often first Whisper/HF model download; wait and retry  

Full recovery table: see prior commits if needed; key rows above still apply.

---

## Current focus (2026-08-24)

1. Local **YouTube** path solid (audio + quality) for owner testing.  
2. Treat **production video fetch** design as governed by `VIDEO_EXTRACTION_ARCHITECTURE.md` — do not double down on cloud yt-dlp.  
3. Transcript-from-**local file** + Gemini remain valuable even under Option A/C (user already has the file).

---

## AI handoff prompt (copy-paste)

> Read `docs/SESSION_NOTES.md`, `docs/VIDEO_EXTRACTION_ARCHITECTURE.md`, and `docs/REVIEW_AND_ROADMAP.md`.  
> **Production:** server-side yt-dlp is deprecated; prefer Option A (extension interception), B (managed APIs), or C (Whop-native).  
> **Local/dev:** yt-dlp YouTube cascade still: DASH 1080 → DASH 720 → progressive; audio probe (T11); never progressive inside HQ string (T13).  
> **Docs rule:** every behavior change updates SESSION_NOTES in the same session.  
> Do not overwrite Claude/Grok cascade fixes without reading T11+T13.
