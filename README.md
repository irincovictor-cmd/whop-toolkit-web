# Whop Toolkit — Web

Web migration of the original Whop Toolkit CLI. See `docs/MIGRATION_PLAN.md`
for the full architecture rationale and module mapping, and
`docs/legacy_cli_docs/` for the complete original CLI, preserved as-is.

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

## Deploying

- **Frontend** → Vercel or Cloudflare Pages. Set the env vars from
  `.env.example` in your hosting dashboard; `WHOP_REDIRECT_URI` and
  `BACKEND_SERVICE_URL` need your real production URLs.
- **Backend** → Render or Railway, using `backend/Dockerfile` directly.
  Both platforms auto-detect a Dockerfile and inject `$PORT`.

## What's Still a Stub vs. Production-Ready

Being direct about this so nothing here gets deployed with false confidence:

- **`app/routes/clips.py`'s `FileResponse`** streams the finished clip
  straight from the container's local disk. That's fine for local dev, but
  on Render/Railway your container's filesystem is ephemeral and requests
  may hit different container instances — for real production traffic,
  swap this for an upload to S3-compatible object storage and return a
  signed URL instead (there's a comment marking exactly where in the file).
- **CORS in `backend/app/main.py`** is wide open (`allow_origins=["*"]`) for
  local dev convenience. Lock it to `FRONTEND_ORIGIN` before deploying
  publicly.
- **No rate limiting or per-user quota enforcement** yet on either the
  clip-extraction or Gemini-analysis routes — both are real costs (compute
  time, API spend) that a public-facing tool needs guardrails on before
  launch. Not built here since it depends on your actual pricing/plan
  model, which wasn't specified.
- **No database yet.** `core/activity_log.py` and `core/project.py`'s
  video-ID-based dedup (see MIGRATION_PLAN.md) both assume a `projects` /
  `activity_log` table exists, keyed by the Whop user's `sub`. Schema and
  an ORM layer (Prisma/Drizzle for the Next.js side, or a shared Postgres
  the backend also reads) aren't included here — worth doing before any
  "recent projects" or per-user history feature is built on the frontend.
