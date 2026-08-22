# Chat Context & Project Memory

> Preserves decisions and workflow from Grok sessions so future chats don’t start from zero.
> Last updated: 2026-08-22 (UI redesign + AI assistant)

## Project
- **Repo:** https://github.com/irincovictor-cmd/whop-toolkit-web
- **Owner:** irincovictor-cmd
- **Branch:** main
- **Local path (Windows):** `C:\Users\Victorjames\Desktop\whop-toolkit-web`

## Permanent Workflow (Claude → Zip → Grok → GitHub)

1. Claude updates the code.
2. You export a **zip** of the project.
3. You send the zip to Grok.
4. Grok extracts it and pushes **only source files** to `main`.
5. Grok **never** pushes:
   - `frontend/.env.local`
   - `backend/.env`
   - any other secrets

Commit message style: short, descriptive (e.g. `Update from latest zip` or design notes).

## Important Commands (Windows)

### Pull latest
```powershell
cd C:\Users\Victorjames\Desktop\whop-toolkit-web
git pull origin main
```

### Run the app
**Backend (Terminal 1):**
```powershell
cd C:\Users\Victorjames\Desktop\whop-toolkit-web\backend
uvicorn app.main:app --reload --port 8000
```

**Frontend (Terminal 2):**
```powershell
cd C:\Users\Victorjames\Desktop\whop-toolkit-web\frontend
npm run dev
```
Open http://localhost:3000

### Push your own local changes (safely)
```powershell
cd C:\Users\Victorjames\Desktop\whop-toolkit-web
git status
git add .
git commit -m "Your message"
git push origin main
```
`.env` / `.env.local` are gitignored — they will not be pushed.

### If GitHub blocks a push (secret detected)
```powershell
git rm --cached frontend/.env.local
git rm --cached backend/.env 2>$null
git commit --amend -m "Update code (without secrets)" --no-edit
git push origin main --force
```

## What was done in these chats

### Zip pushes
- Pushed `whop-toolkit-web-updated` zips (download feature, ytdlp cascade, transcript updates, validators).
- Restored full `ToolkitApp.tsx` after a temporary placeholder issue.
- Added AI Assistant: `frontend/components/AiHelper.tsx` + `frontend/app/api/ai/assistant/route.ts`.
- Updated `dashboard/layout.tsx` to mount the floating AI helper.
- **Never** committed `.env` / `.env.local` after the first secret-block incident.

### UI redesign (Grok, not Claude)
Claude fixed bugs but left everything on one crowded page. Grok redesigned the workspace:

| Mode tab | Purpose |
|----------|---------|
| **Download** | Full video only — format + download |
| **Clip** | Timestamps, aspect, fit, quality, max size |
| **Transcript** | Fetch captions, scrollable list, .srt / .txt |
| **Analyze** | Gemini virality score, tags, suggested clips |

Also:
- Compact video header (thumbnail + title) instead of a huge competing card
- More spacing / clearer hierarchy
- Tailwind `content` includes `./components/**` so AiHelper styles work

### Docs in repo
- `docs/CHAT_CONTEXT.md` — this file
- `docs/SESSION_NOTES.md` — YouTube SABR/quality, local paths
- `docs/REVIEW_AND_ROADMAP.md` — bugs, P0–P3
- `docs/MIGRATION_PLAN.md` — CLI → web

## Key technical notes
- Frontend: Next.js 15 (App Router), Tailwind, dark theme (`ink` / `accent` / `mist`)
- Backend: FastAPI + yt-dlp + faster-whisper
- Local auth: `DEV_SKIP_AUTH=true` in `frontend/.env.local`
- Backend URL: `BACKEND_SERVICE_URL=http://localhost:8000`
- Gemini: `GEMINI_API_KEY` in `frontend/.env.local` (server-side only)

## Next time you open a new chat
Say:

> Continue from `docs/CHAT_CONTEXT.md` – same workflow (zip → push). Env files never pushed.

Grok will follow that workflow and keep design/docs in sync.
