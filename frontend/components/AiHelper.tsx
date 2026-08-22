"use client";

/**
 * Floating "Ask AI" helper -- lives in the dashboard shell (see
 * app/dashboard/layout.tsx) so it's reachable from every tab, not just the
 * Workspace. Talks to /api/ai/assistant, which is scoped by system prompt
 * to this app + video/audio/clip/trend/Whop topics -- see that route for
 * the actual scope definition.
 */

import { useEffect, useRef, useState } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const STARTER_PROMPTS = [
  "Why did my clip download at a lower quality?",
  "Best aspect ratio for TikTok vs YouTube Shorts?",
  "How do I sell clips as a Whop membership perk?",
];

export default function AiHelper() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  async function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || busy) return;

    const next: Message[] = [...messages, { role: "user", content: trimmed }];
    setMessages(next);
    setInput("");
    setError(null);
    setBusy(true);

    try {
      const res = await fetch("/api/ai/assistant", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: next }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Assistant failed to respond");
      setMessages([...next, { role: "assistant", content: data.reply || "…" }]);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Assistant failed to respond");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {open && (
        <div className="fixed bottom-24 right-5 z-50 flex h-[32rem] w-[22rem] max-w-[calc(100vw-2.5rem)] flex-col overflow-hidden rounded-2xl border border-ink-border bg-ink-surface shadow-2xl shadow-black/40">
          <div className="flex items-center justify-between border-b border-ink-border bg-ink-raised/50 px-4 py-3">
            <div>
              <p className="text-sm font-semibold text-mist">Toolkit Assistant</p>
              <p className="text-[11px] text-mist-muted">Video · audio · clips · trends · Whop</p>
            </div>
            <button
              onClick={() => setOpen(false)}
              aria-label="Close assistant"
              className="rounded-lg p-1.5 text-mist-muted transition hover:bg-ink-raised hover:text-mist"
            >
              ✕
            </button>
          </div>

          <div ref={scrollRef} className="scroll-dark flex-1 space-y-3 overflow-y-auto px-4 py-4">
            {messages.length === 0 && (
              <div className="space-y-3">
                <p className="text-xs text-mist-muted">
                  Ask about using the toolkit, editing/audio choices, clip strategy, or Whop.
                </p>
                <div className="space-y-2">
                  {STARTER_PROMPTS.map((p) => (
                    <button
                      key={p}
                      onClick={() => send(p)}
                      className="block w-full rounded-xl border border-ink-border bg-ink-raised px-3 py-2 text-left text-xs text-mist-muted transition hover:border-accent/40 hover:text-mist"
                    >
                      {p}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m, i) => (
              <div
                key={i}
                className={`max-w-[85%] rounded-xl px-3 py-2 text-sm leading-relaxed ${
                  m.role === "user"
                    ? "ml-auto bg-accent text-white"
                    : "bg-ink-raised text-mist"
                }`}
              >
                {m.content}
              </div>
            ))}

            {busy && (
              <div className="flex w-fit items-center gap-1 rounded-xl bg-ink-raised px-3 py-2">
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-mist-muted [animation-delay:-0.2s]" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-mist-muted [animation-delay:-0.1s]" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-mist-muted" />
              </div>
            )}

            {error && (
              <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300">
                {error}
              </p>
            )}
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
            className="flex items-center gap-2 border-t border-ink-border p-3"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask the assistant…"
              className="flex-1 rounded-lg border border-ink-border bg-ink-raised px-3 py-2 text-sm text-mist placeholder:text-mist-muted/60 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
            />
            <button
              type="submit"
              disabled={!input.trim() || busy}
              className="rounded-lg bg-accent px-3 py-2 text-sm font-semibold text-white transition hover:bg-accent-hover disabled:opacity-50"
            >
              Send
            </button>
          </form>
        </div>
      )}

      <button
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "Close assistant" : "Open assistant"}
        className="fixed bottom-6 right-5 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-accent text-white shadow-lg shadow-accent/30 transition hover:bg-accent-hover hover:scale-105"
      >
        {open ? (
          <span className="text-xl leading-none">✕</span>
        ) : (
          <span className="text-xl leading-none">✦</span>
        )}
      </button>
    </>
  );
}
