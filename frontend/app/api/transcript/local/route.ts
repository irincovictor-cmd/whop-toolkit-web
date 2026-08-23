/**
 * POST /api/transcript/local
 *
 * Thin proxy to the backend's /transcript/local endpoint (see
 * backend/app/routes/transcript.py) -- transcribes a video file already on
 * the user's device (e.g. something downloaded earlier) via Whisper,
 * mirroring the CLI tool's local-import transcript flow. Distinct from
 * /api/transcript, which works from a pasted URL.
 */

import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/whop-session";

const BACKEND_URL = process.env.BACKEND_SERVICE_URL!; // e.g. https://your-backend.onrender.com

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  const contentType = req.headers.get("content-type") || "";
  if (!contentType.includes("multipart/form-data")) {
    return NextResponse.json({ error: "Expected a multipart file upload" }, { status: 400 });
  }

  const backendRes = await fetch(`${BACKEND_URL}/transcript/local`, {
    method: "POST",
    headers: { "Content-Type": contentType },
    body: req.body,
    // @ts-expect-error -- duplex is required by undici/Node fetch when the
    // request body is a stream, but isn't yet in the TS lib fetch types.
    duplex: "half",
  });

  const data = await backendRes.json().catch(() => ({}));
  if (!backendRes.ok) {
    return NextResponse.json(
      { error: data.error || data.detail || "Local transcript failed" },
      { status: backendRes.status }
    );
  }
  return NextResponse.json(data);
}
