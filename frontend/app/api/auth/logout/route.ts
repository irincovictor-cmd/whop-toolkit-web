import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const SESSION_COOKIE_NAME = "whop_session";

export async function POST(req: NextRequest) {
  (await cookies()).delete(SESSION_COOKIE_NAME);
  return NextResponse.redirect(new URL("/login", req.url));
}
