/**
 * POST /api/clips
 *
 * Thin proxy to the backend microservice's /clips/extract endpoint (see
 * backend/app/routes/clips.py). This route never touches yt-dlp/ffmpeg
 * itself -- see docs/MIGRATION_PLAN.md #2 for why that boundary is
 * non-negotiable on serverless hosting.
 */

import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/whop-session";
import { validateClipRequest } from "@/lib/validators";

const BACKEND_URL = process.env.BACKEND_SERVICE_URL!; // e.g. https://your-backend.onrender.com

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  const body = await req.json();
  const validationError = validateClipRequest(body);
  if (validationError) {
    return NextResponse.json({ error: validationError }, { status: 400 });
  }

  const backendRes = await fetch(`${BACKEND_URL}/clips/extract`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!backendRes.ok) {
    const detail = await backendRes.json().catch(() => ({}));
    return NextResponse.json({ error: detail.detail || "Clip extraction failed" }, { status: backendRes.status });
  }

  // Stream the file straight through rather than buffering it in memory.
  return new NextResponse(backendRes.body, {
    headers: {
      "Content-Type": backendRes.headers.get("Content-Type") || "application/octet-stream",
      "Content-Disposition": backendRes.headers.get("Content-Disposition") || "attachment",
      "X-Video-Quality": backendRes.headers.get("X-Video-Quality") || "",
    },
  });
}
