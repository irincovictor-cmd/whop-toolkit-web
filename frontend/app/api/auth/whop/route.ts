/**
 * GET /api/auth/whop
 *
 * Step 1 of Whop's OAuth 2.1 + PKCE flow: build a code_verifier/challenge
 * pair server-side and redirect the user to Whop's authorize endpoint.
 *
 * This runs as a Next.js Route Handler rather than client-side browser code,
 * since PKCE's verifier needs to survive the redirect round-trip without
 * exposing it to the client at all -- an httpOnly cookie does that; browser
 * sessionStorage (the pattern used in client-side SPA examples) does not
 * apply cleanly to a server-rendered app like this one.
 */

import { NextRequest, NextResponse } from "next/server";
import { randomBytes, createHash } from "crypto";
import { authCookieOptions } from "@/lib/cookie-options";

const WHOP_AUTHORIZE_URL = "https://api.whop.com/oauth/authorize";
const PKCE_COOKIE_NAME = "whop_pkce";

function base64url(buf: Buffer): string {
  return buf.toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export async function GET(req: NextRequest) {
  const clientId = process.env.NEXT_PUBLIC_WHOP_APP_ID;
  const redirectUri = process.env.WHOP_REDIRECT_URI; // e.g. https://yourapp.com/api/auth/callback

  if (!clientId || !redirectUri) {
    return NextResponse.json({ error: "Whop OAuth is not configured" }, { status: 500 });
  }

  const codeVerifier = base64url(randomBytes(32));
  const codeChallenge = base64url(createHash("sha256").update(codeVerifier).digest());
  const state = base64url(randomBytes(16));

  const params = new URLSearchParams({
    response_type: "code",
    client_id: clientId,
    redirect_uri: redirectUri,
    scope: "openid profile email",
    state,
    code_challenge: codeChallenge,
    code_challenge_method: "S256",
  });

  const response = NextResponse.redirect(`${WHOP_AUTHORIZE_URL}?${params.toString()}`);

  // Store the verifier + state server-side in an httpOnly cookie -- never
  // sent to client JS, only readable by the callback route handler below.
  response.cookies.set(PKCE_COOKIE_NAME, JSON.stringify({ codeVerifier, state }), authCookieOptions(600));

  return response;
}
