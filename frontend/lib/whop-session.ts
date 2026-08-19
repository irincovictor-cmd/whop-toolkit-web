/**
 * Server-side helpers for reading/refreshing the Whop session cookie set
 * by app/api/auth/callback/route.ts. Import this in any Route Handler
 * that needs to know who's logged in -- never read the cookie directly
 * elsewhere, so the refresh logic stays in exactly one place.
 */

import { cookies } from "next/headers";
import { authCookieOptions } from "@/lib/cookie-options";

const SESSION_COOKIE_NAME = "whop_session";
const WHOP_TOKEN_URL = "https://api.whop.com/oauth/token";
const WHOP_USERINFO_URL = "https://api.whop.com/oauth/userinfo";

interface WhopSession {
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
}

export async function getSession(): Promise<WhopSession | null> {
  if (process.env.DEV_SKIP_AUTH === "true") {
    return {
      accessToken: "dev",
      refreshToken: "dev",
      expiresAt: Date.now() + 86400000,
    };
  }

  const raw = (await cookies()).get(SESSION_COOKIE_NAME)?.value;
  if (!raw) return null;

  let session: WhopSession = JSON.parse(raw);

  // Refresh proactively if within 5 minutes of expiry -- same buffer the
  // CLI's equivalent-in-spirit caching logic used elsewhere in this project.
  if (Date.now() > session.expiresAt - 5 * 60 * 1000) {
    session = await refreshSession(session.refreshToken);
  }

  return session;
}

async function refreshSession(refreshToken: string): Promise<WhopSession> {
  const clientId = process.env.NEXT_PUBLIC_WHOP_APP_ID!;

  const res = await fetch(WHOP_TOKEN_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      grant_type: "refresh_token",
      refresh_token: refreshToken,
      client_id: clientId,
    }),
  });

  if (!res.ok) {
    throw new Error("Session expired -- please log in again");
  }

  const tokens = await res.json();
  const newSession: WhopSession = {
    accessToken: tokens.access_token,
    refreshToken: tokens.refresh_token,
    expiresAt: Date.now() + tokens.expires_in * 1000,
  };

  (await cookies()).set(SESSION_COOKIE_NAME, JSON.stringify(newSession), authCookieOptions(60 * 60 * 24 * 30));

  return newSession;
}

export async function getUserInfo(accessToken: string) {
  const res = await fetch(WHOP_USERINFO_URL, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) throw new Error(`Failed to fetch user info: ${res.status}`);
  return res.json();
}
