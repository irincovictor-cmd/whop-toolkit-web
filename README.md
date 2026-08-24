# Whop Toolkit — Web

Web migration of the original Whop Toolkit CLI. See `docs/MIGRATION_PLAN.md`
for CLI→web mapping, and `docs/legacy_cli_docs/` for the frozen CLI.

**Start here before any change or AI handoff:**

1. **`docs/SESSION_NOTES.md`** — pinned session: YouTube quality, local paths, UI↔API matrix  
2. **`docs/VIDEO_EXTRACTION_ARCHITECTURE.md`** — **production** video extraction direction (server yt-dlp deprecated)  
3. **`docs/REVIEW_AND_ROADMAP.md`** — bugs, P0–P3, product requirements  

**UI prototype (Figma):** [Whop Toolkit — UI Prototype](https://www.figma.com/design/NNmXpsosmbC3fPIZICfZOs)

### Product intent (summary)

- **Local/dev:** YouTube-first via yt-dlp; other platforms best-effort.  
- **Production extraction:** not “scale server yt-dlp” — see architecture spec (browser extension / managed APIs / Whop-native).  
- **Model:** process briefly → user downloads (not a media library).  
- **Export:** aspect / fit / quality in UI; backend application still roadmap P2.  

## Quick Start (local dev)

**Backend:**
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# set LOCAL_OUTPUT_DIR to a folder on disk for local clip copies
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
cp .env.example .env.local   # BACKEND_SERVICE_URL=http://localhost:8000, DEV_SKIP_AUTH=true for UI-only
npm run dev
```

Visit `http://localhost:3000`.

> `DEV_SKIP_AUTH=true` is local only. Never enable in production.

Keep yt-dlp fresh when YouTube breaks downloads (local only):
```bash
pip install -U --pre "yt-dlp[default]"
```

## Deploying

- **Frontend** → Vercel or Cloudflare Pages  
- **Backend** → Render / Railway / VPS via `backend/Dockerfile`  

Before investing in multi-user cloud download, read **`docs/VIDEO_EXTRACTION_ARCHITECTURE.md`**. Whisper + server-side fetch need real CPU/RAM; yt-dlp on datacenter IPs is fragile.

## Docs map

| Doc | What it’s for |
|-----|----------------|
| `docs/SESSION_NOTES.md` | Pinned local session findings (YouTube, wiring, bugs) |
| `docs/VIDEO_EXTRACTION_ARCHITECTURE.md` | **Production** extraction strategy (Options A/B/C) |
| `docs/REVIEW_AND_ROADMAP.md` | Bugs, priorities, product requirements |
| `docs/MIGRATION_PLAN.md` | CLI → web mapping |
| `docs/DIRECTORY_STRUCTURE.md` | Folders |
| `docs/legacy_cli_docs/` | Original CLI |

## Honest stubs

- Clips via `FileResponse` / optional `LOCAL_OUTPUT_DIR` — not S3 yet  
- CORS may still be open; lock with `FRONTEND_ORIGIN`  
- No backend internal auth key yet  
- Export aspect/fit not applied in ffmpeg yet  
- No DB / rate limits / convert UI  
