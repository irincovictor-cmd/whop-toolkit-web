# Directory Structure

```
whop-toolkit-web/
│
├── frontend/                          # Next.js (App Router) + Tailwind — deploy to Vercel/Cloudflare Pages
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth/
│   │   │   │   ├── whop/route.ts          # Step 1: builds PKCE challenge, redirects to Whop
│   │   │   │   └── callback/route.ts      # Step 2: exchanges code for tokens, sets session cookie
│   │   │   ├── clips/
│   │   │   │   └── route.ts               # Proxies timestamp-trim requests to the backend microservice
│   │   │   ├── transcript/
│   │   │   │   └── route.ts               # Proxies transcript requests to the backend microservice
│   │   │   └── ai/
│   │   │       └── analyze/route.ts       # Gemini: summary + virality scoring (server-side only)
│   │   ├── (dashboard)/
│   │   │   ├── page.tsx                   # Main app UI: paste URL, pick timestamps/format
│   │   │   └── layout.tsx
│   │   ├── login/page.tsx                 # "Sign in with Whop" entry point
│   │   └── layout.tsx
│   ├── lib/
│   │   ├── whop-session.ts                # Cookie-based session read/write helpers (server-side)
│   │   └── validators.ts                  # Ported from modules/clip_selector.py's duration-bounds checks
│   ├── package.json
│   ├── tailwind.config.ts
│   └── .env.example
│
├── backend/                           # Python microservice — deploy to Render/Railway via Docker
│   ├── app/
│   │   ├── main.py                        # FastAPI app, route registration
│   │   ├── routes/
│   │   │   ├── metadata.py                # from modules/metadata.py
│   │   │   ├── clips.py                   # from modules/downloader.py (stream-crop, --download-sections)
│   │   │   ├── transcript.py              # from modules/transcript.py (captions + faster-whisper fallback)
│   │   │   └── convert.py                 # from modules/converter.py
│   │   └── core/
│   │       └── ytdlp_client.py            # shared yt-dlp options builder (was modules/metadata.py:build_ydl_options)
│   ├── requirements.txt
│   └── Dockerfile
│
└── docs/
    ├── MIGRATION_PLAN.md               # this migration's architecture rationale
    ├── DIRECTORY_STRUCTURE.md          # this file
    └── legacy_cli_docs/                 # full historical record of the original CLI
        ├── ARCHITECTURE.md
        ├── DEVELOPER_GUIDE.md
        ├── USER_GUIDE.md
        ├── SHARING_GUIDE.md
        ├── CHANGELOG.md
        ├── ROADMAP.md
        ├── MIGRATING_TO_DATA_FOLDER.md
        └── cli_source/                  # original whop.py, config.py, core/, modules/, classes/ -- untouched
```

## Why frontend/backend are two separate deployable units, not a monorepo app

Vercel/Cloudflare Pages and Render/Railway are different deployment targets
with different constraints (see MIGRATION_PLAN.md §2). Keeping them as two
top-level folders with independent `package.json` / `requirements.txt` means
each can be deployed, scaled, and rolled back independently — the frontend
redeploying doesn't require rebuilding the Docker image, and vice versa.
