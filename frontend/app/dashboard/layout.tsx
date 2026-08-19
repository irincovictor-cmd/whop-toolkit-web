import Link from "next/link";
import { redirect } from "next/navigation";
import { getSession } from "@/lib/whop-session";

const NAV = [
  { href: "/dashboard", label: "Workspace" },
  { href: "/dashboard#projects", label: "Projects" },
  { href: "/dashboard#history", label: "History" },
  { href: "/dashboard#settings", label: "Settings" },
];

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const session = await getSession();
  if (!session) {
    redirect("/login");
  }

  return (
    <div className="flex min-h-screen bg-ink">
      <aside className="hidden w-60 shrink-0 flex-col border-r border-ink-border bg-ink-surface md:flex">
        <div className="flex items-center gap-3 px-5 py-6">
          <div className="h-8 w-8 rounded-lg bg-accent" />
          <span className="text-sm font-semibold text-mist">Whop Toolkit</span>
        </div>

        <nav className="flex flex-1 flex-col gap-1 px-3">
          {NAV.map((item, i) => (
            <Link
              key={item.label}
              href={item.href}
              className={`rounded-xl px-3 py-2.5 text-sm transition ${
                i === 0
                  ? "bg-ink-raised font-semibold text-mist"
                  : "text-mist-muted hover:bg-ink-raised/60 hover:text-mist"
              }`}
            >
              <span className="mr-2 inline-block h-1.5 w-1.5 rounded-full bg-current opacity-70" />
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="border-t border-ink-border px-5 py-4">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-full bg-[#4D8CFF]" />
            <div className="min-w-0">
              <p className="truncate text-xs font-medium text-mist">You · Whop</p>
              <p className="truncate text-[11px] text-mist-muted">Signed in</p>
            </div>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-ink-border px-4 py-4 md:px-8">
          <h1 className="text-base font-semibold text-mist md:text-lg">Workspace</h1>
          <form action="/api/auth/logout" method="POST">
            <button
              type="submit"
              className="text-sm text-mist-muted transition hover:text-mist"
            >
              Sign out
            </button>
          </form>
        </header>
        <main className="flex-1 px-4 py-6 md:px-8">{children}</main>
      </div>
    </div>
  );
}
