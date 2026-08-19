import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-ink px-4 text-center">
      <h1 className="text-2xl font-semibold text-mist">Page not found</h1>
      <p className="mt-2 text-sm text-mist-muted">That route does not exist.</p>
      <Link href="/" className="mt-6 text-sm font-medium text-accent hover:text-accent-hover">
        Go home
      </Link>
    </main>
  );
}
