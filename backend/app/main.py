"""
Whop Toolkit backend microservice.

Runs yt-dlp/ffmpeg/faster-whisper inside a long-running Docker container --
never inside a Next.js serverless function (see docs/MIGRATION_PLAN.md #2
for why). The frontend only ever talks to this service over HTTP; it never
shells out to these tools itself.

This is the direct successor to whop.py's role as an orchestrator, except
instead of a CLI menu dispatching to modules/*.py functions, FastAPI routes
dispatch to the equivalent route modules below.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import metadata, clips, transcript, convert, download

app = FastAPI(title="Whop Toolkit Backend", version="1.0.0")

# Only the Next.js frontend's origin should be able to call this service
# directly in production. FRONTEND_ORIGIN can be a single origin or a
# comma-separated list (e.g. local dev + deployed frontend); unset/empty
# falls back to "*" for local dev only -- this is the B5 item in
# docs/REVIEW_AND_ROADMAP.md, set FRONTEND_ORIGIN before deploying.
_frontend_origin = os.getenv("FRONTEND_ORIGIN", "").strip()
_allow_origins = [o.strip() for o in _frontend_origin.split(",") if o.strip()] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(metadata.router, prefix="/metadata", tags=["metadata"])
app.include_router(clips.router, prefix="/clips", tags=["clips"])
app.include_router(transcript.router, prefix="/transcript", tags=["transcript"])
app.include_router(convert.router, prefix="/convert", tags=["convert"])
app.include_router(download.router, prefix="/download", tags=["download"])


@app.get("/health")
def health():
    """Render/Railway health check target."""
    return {"status": "ok"}
