/**
 * GET /api/auth/callback
 *
 * Step 2 of Whop's OAuth 2.1 + PKCE flow. Whop redirects here with
 * ?code=...&state=.... Verifies state against the cookie set in
 * /api/auth/whop, exchanges the code + verifier for tokens server-side
 * (the client never sees the code_verifier or the client_secret), and
 * sets a session cookie for the app to use.
 */

import { NextRequest, NextResponse } from "next/server";
import { authCookieOptions } from "@/lib/cookie-options";

const WHOP_TOKEN_URL = "https://api.whop.com/oauth/token";
const PKCE_COOKIE_NAME = "whop_pkce";
const SESSION_COOKIE_NAME = "whop_session";

interface WhopTokenResponse {
  access_token: string;
  refresh_token: string;
  id_token?: string;
  token_type: string;
  expires_in: number;
}

export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const code = url.searchParams.get("code");
  const returnedState = url.searchParams.get("state");
  const error = url.searchParams.get("error");

  if (error) {
    return NextResponse.redirect(
      new URL(`/login?error=${encodeURIComponent(error)}`, req.url)
    );
  }

  const pkceCookie = req.cookies.get(PKCE_COOKIE_NAME)?.value;
  if (!pkceCookie) {
    return NextResponse.redirect(new URL("/login?error=missing_pkce_state", req.url));
  }

  const { codeVerifier, state } = JSON.parse(pkceCookie);
  if (returnedState !== state) {
    return NextResponse.redirect(new URL("/login?error=state_mismatch", req.url));
  }

  const clientId = process.env.NEXT_PUBLIC_WHOP_APP_ID!;
  const redirectUri = process.env.WHOP_REDIRECT_URI!;

  const tokenRes = await fetch(WHOP_TOKEN_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      grant_type: "authorization_code",
      code,
      redirect_uri: redirectUri,
      client_id: clientId,
      code_verifier: codeVerifier,
    }),
  });

  if (!tokenRes.ok) {
    const errBody = await tokenRes.json().catch(() => ({}));
    return NextResponse.redirect(
      new URL(`/login?error=${encodeURIComponent(errBody.error_description || "token_exchange_failed")}`, req.url)
    );
  }

  const tokens: WhopTokenResponse = await tokenRes.json();

  const response = NextResponse.redirect(new URL("/dashboard", req.url));

  // Session cookie holds the access token server-side only. The frontend
  // never handles raw tokens directly -- every authenticated API call goes
  // through a Next.js route handler that reads this cookie itself.
  response.cookies.set(SESSION_COOKIE_NAME, JSON.stringify({
    accessToken: tokens.access_token,
    refreshToken: tokens.refresh_token,
    expiresAt: Date.now() + tokens.expires_in * 1000,
  }), authCookieOptions(60 * 60 * 24 * 30));

  response.cookies.delete(PKCE_COOKIE_NAME);

  return response;
}
