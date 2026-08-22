# Chat Context & Project Memory

> This file preserves the important decisions and workflow from the Grok chat (Aug 22, 2026) so future sessions don’t start from zero.

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

Commit message style:  
`Update frontend and backend from latest zip` (or whatever you request)

## Important Commands (Windows)

### Pull latest code
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
Then open http://localhost:3000

### Push your own local changes (safely)
```powershell
cd C:\Users\Victorjames\Desktop\whop-toolkit-web
git status
git add .
git commit -m "Your message"
git push origin main
```
`.env` / `.env.local` are already ignored — they will not be pushed.

### If GitHub blocks a push because of a secret
```powershell
git rm --cached frontend/.env.local
git rm --cached backend/.env 2>$null
git commit --amend -m "Update code (without secrets)" --no-edit
git push origin main --force
```

## What was done in this chat
- Extracted and pushed the zip `whop-toolkit-web-updated (1).zip`
- Added full-video download feature (`/api/download` + backend route)
- Updated `ytdlp_client.py` (shared `base_cli_flags` + format cascade)
- Updated `transcript.py`, `validators.ts`, `main.py`
- Restored the full `ToolkitApp.tsx` (was temporarily overwritten)
- Removed secrets from git history so GitHub push protection stopped blocking
- Confirmed force-push of clean code succeeded

## Key technical notes
- Frontend: Next.js 15 (App Router)
- Backend: FastAPI + yt-dlp + faster-whisper
- Local auth bypass: `DEV_SKIP_AUTH=true` in `frontend/.env.local`
- Backend URL for local: `BACKEND_SERVICE_URL=http://localhost:8000`
- Gemini key goes in `frontend/.env.local` as `GEMINI_API_KEY=...`

## Next time you open a new chat
Just say:  
“Continue from docs/CHAT_CONTEXT.md – same workflow (zip → push)”

Grok will know exactly what to do.
