export default function NotFound() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8 text-center">
      <h1 className="text-2xl font-semibold mb-2">Page not found</h1>
      <a href="/" className="text-blue-600 hover:underline">
        Go home
      </a>
    </main>
  );
}
