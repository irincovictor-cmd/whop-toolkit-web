const ERROR_MESSAGES: Record<string, string> = {
  missing_pkce_state: "Login session expired. Please try again.",
  state_mismatch: "Security check failed. Please try signing in again.",
  token_exchange_failed: "Could not complete sign-in with Whop.",
};

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await searchParams;
  const message = error ? (ERROR_MESSAGES[error] ?? decodeURIComponent(error)) : null;

  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-4">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(115,89,250,0.18),_transparent_55%)]" />

      <div className="relative w-full max-w-md rounded-2xl border border-ink-border bg-ink-surface p-8 shadow-glow">
        <div className="mb-6 flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-accent" />
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-mist">Whop Toolkit</h1>
            <p className="text-xs text-mist-muted">Creator clip &amp; transcript workspace</p>
          </div>
        </div>

        <p className="mb-6 text-sm leading-relaxed text-mist-muted">
          Sign in with Whop to fetch videos, cut clips, pull transcripts, and run Gemini analysis —
          without keeping a permanent media library.
        </p>

        {message && (
          <p className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            {message}
          </p>
        )}

        <a
          href="/api/auth/whop"
          className="flex w-full items-center justify-center rounded-xl bg-accent px-4 py-3 text-sm font-semibold text-white transition hover:bg-accent-hover"
        >
          Sign in with Whop
        </a>

        <p className="mt-6 text-center text-xs text-mist-muted">
          Local dev: set <code className="rounded bg-ink-raised px-1">DEV_SKIP_AUTH=true</code> in{" "}
          <code className="rounded bg-ink-raised px-1">.env.local</code> to skip OAuth.
        </p>
      </div>
    </main>
  );
}
