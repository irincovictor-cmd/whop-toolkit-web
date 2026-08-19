import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/whop-session";

const BACKEND_URL = process.env.BACKEND_SERVICE_URL!;

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  const body = await req.json();
  if (!body.url) {
    return NextResponse.json({ error: "url is required" }, { status: 400 });
  }

  const backendRes = await fetch(`${BACKEND_URL}/transcript`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const data = await backendRes.json().catch(() => ({}));
  if (!backendRes.ok) {
    return NextResponse.json({ error: data.detail || "Transcript fetch failed" }, { status: backendRes.status });
  }

  return NextResponse.json(data);
}
