# Whop Toolkit — Web

Web migration of the original Whop Toolkit CLI. See `docs/MIGRATION_PLAN.md`
for the full architecture rationale and module mapping, and
`docs/legacy_cli_docs/` for the complete original CLI, preserved as-is.

**Status, bugs, product requirements, and prioritized fixes:** always read  
→ **`docs/REVIEW_AND_ROADMAP.md`**  
before changing code or handing work to another AI. That file is the short
handoff doc so prompts stay small.

**UI prototype (Figma):** [Whop Toolkit — UI Prototype](https://www.figma.com/design/NNmXpsosmbC3fPIZICfZOs)

### Product intent (summary)

- **Sources:** YouTube, TikTok, Instagram, X, Vimeo; **Facebook planned**. Full downloads where yt-dlp allows; watermark-free is **best-effort** (platforms change).
- **Export:** not only mp4/mp3/wav — also **aspect** (original / 9:16 / 16:9), **fit** (letterbox vs cover zoom-fill), **quality** (720 / 1080 / source), optional max MB. Portrait + Cover must not silently side-slice; see roadmap § Product requirements.

Implementation of those export controls still lags the UI prototype and docs.

## Quick Start (local dev)

**Backend:**
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
cp .env.example .env.local   # fill in Whop app credentials + Gemini API key
npm run dev
```

Visit `http://localhost:3000`, click "Sign in with Whop" (wire this up to
`GET /api/auth/whop` in your login page), and you're in.

> Set `DEV_SKIP_AUTH=true` in `.env.local` to skip Whop login while testing UI/backend locally. Never enable that in production.

## Deploying

- **Frontend** → Vercel or Cloudflare Pages. Set the env vars from
  `.env.example` in your hosting dashboard; `WHOP_REDIRECT_URI` and
  `BACKEND_SERVICE_URL` need your real production URLs.
- **Backend** → Render or Railway, using `backend/Dockerfile` directly.
  Both platforms auto-detect a Dockerfile and inject `$PORT`.

## Docs map

| Doc | What it’s for |
|-----|----------------|
| `docs/REVIEW_AND_ROADMAP.md` | **Start here** — product requirements, bugs, P0–P3 |
| `docs/MIGRATION_PLAN.md` | CLI → web module mapping and why the backend is separate |
| `docs/DIRECTORY_STRUCTURE.md` | Folder layout |
| `docs/legacy_cli_docs/` | Original CLI architecture, guides, and frozen source |

## What's Still a Stub vs. Production-Ready

Being direct so nothing gets deployed with false confidence. Full detail and
fix order live in `docs/REVIEW_AND_ROADMAP.md`.

- **`backend/app/routes/clips.py` `FileResponse`** — streams from container disk (local-dev only). Production needs S3-compatible storage + signed URL.
- **CORS** — still wide open (`*`) until locked to `FRONTEND_ORIGIN` (see roadmap B5).
- **No backend-side auth** — frontend checks Whop session; FastAPI itself is open if the URL is known (roadmap B6).
- **Export aspect / fit / quality** — documented + in Figma; not fully wired in web UI/API yet.
- **No rate limiting / quotas** — clip extraction and Gemini both cost money/compute.
- **No database** — no per-user projects or activity history yet.
- **Repo hygiene** — add/respect `.gitignore`; do not commit `.next`, `__pycache__`, or real `.env` files.
