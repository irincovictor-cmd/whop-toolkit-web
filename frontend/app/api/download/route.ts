/**
 * POST /api/download
 *
 * Thin proxy to the backend microservice's /download endpoint (see
 * backend/app/routes/download.py) -- full-video download for any
 * yt-dlp-supported platform (YouTube, TikTok, Instagram, X/Twitter,
 * Facebook, Vimeo, etc.), as opposed to /api/clips which cuts a
 * timestamped section. Same streaming-through pattern as /api/clips:
 * never buffers the file, never touches yt-dlp/ffmpeg itself.
 */

import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/whop-session";
import { validateDownloadRequest } from "@/lib/validators";

const BACKEND_URL = process.env.BACKEND_SERVICE_URL!; // e.g. https://your-backend.onrender.com

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  const body = await req.json();
  const validationError = validateDownloadRequest(body);
  if (validationError) {
    return NextResponse.json({ error: validationError }, { status: 400 });
  }

  const backendRes = await fetch(`${BACKEND_URL}/download`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!backendRes.ok) {
    const detail = await backendRes.json().catch(() => ({}));
    return NextResponse.json(
      { error: detail.detail || "Video download failed" },
      { status: backendRes.status }
    );
  }

  return new NextResponse(backendRes.body, {
    headers: {
      "Content-Type": backendRes.headers.get("Content-Type") || "application/octet-stream",
      "Content-Disposition": backendRes.headers.get("Content-Disposition") || "attachment",
    },
  });
}
