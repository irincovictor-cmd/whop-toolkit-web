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
    <main className="flex min-h-screen flex-col items-center justify-center p-8 text-center">
      <h1 className="text-4xl font-bold tracking-tight mb-4">Whop Toolkit</h1>
      <p className="text-lg text-gray-600 mb-8 max-w-md">
        Sign in with your Whop account to extract video clips and analyze transcripts with Gemini AI.
      </p>

      {message && (
        <p className="mb-6 max-w-md rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {message}
        </p>
      )}

      <a
        href="/api/auth/whop"
        className="px-6 py-3 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 transition-colors"
      >
        Sign in with Whop
      </a>

      <p className="mt-8 text-sm text-gray-500 max-w-md">
        Local dev requires real Whop app credentials in{" "}
        <code className="rounded bg-gray-100 px-1">frontend/.env.local</code>. See the README for setup.
      </p>
    </main>
  );
}
