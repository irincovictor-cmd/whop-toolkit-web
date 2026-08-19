import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/whop-session";

const BACKEND_URL = process.env.BACKEND_SERVICE_URL!;

export async function GET(req: NextRequest) {
  const session = await getSession();
  if (!session) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  const url = req.nextUrl.searchParams.get("url");
  if (!url) {
    return NextResponse.json({ error: "url query param is required" }, { status: 400 });
  }

  const backendRes = await fetch(`${BACKEND_URL}/metadata?url=${encodeURIComponent(url)}`);
  const data = await backendRes.json().catch(() => ({}));

  if (!backendRes.ok) {
    return NextResponse.json({ error: data.detail || "Metadata fetch failed" }, { status: backendRes.status });
  }

  return NextResponse.json(data);
}
