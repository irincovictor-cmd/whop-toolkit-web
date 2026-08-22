"use client";

/**
 * Floating "Ask AI" helper -- bottom-left so it doesn't fight the main workspace.
 * Compact panel so the input stays on screen without scrolling the page.
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

/** Sit just to the right of the md sidebar (w-60 = 15rem) on desktop; left edge on mobile */
const POS = "left-5 md:left-[16.5rem]";

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
        <div
          className={`fixed bottom-20 z-50 flex h-[20rem] w-[18.5rem] max-w-[calc(100vw-2.5rem)] flex-col overflow-hidden rounded-2xl border border-ink-border bg-ink-surface shadow-2xl shadow-black/40 sm:h-[22rem] sm:w-[20rem] ${POS}`}
        >
          <div className="flex shrink-0 items-center justify-between border-b border-ink-border bg-ink-raised/50 px-3 py-2.5">
            <div>
              <p className="text-sm font-semibold text-mist">Toolkit Assistant</p>
              <p className="text-[10px] text-mist-muted">Video · clips · trends · Whop</p>
            </div>
            <button
              onClick={() => setOpen(false)}
              aria-label="Close assistant"
              className="rounded-lg p-1.5 text-mist-muted transition hover:bg-ink-raised hover:text-mist"
            >
              ✕
            </button>
          </div>

          <div ref={scrollRef} className="scroll-dark min-h-0 flex-1 space-y-2 overflow-y-auto px-3 py-3">
            {messages.length === 0 && (
              <div className="space-y-2">
                <p className="text-[11px] text-mist-muted">
                  Ask about the toolkit, editing, clips, or Whop.
                </p>
                <div className="space-y-1.5">
                  {STARTER_PROMPTS.map((p) => (
                    <button
                      key={p}
                      onClick={() => send(p)}
                      className="block w-full rounded-lg border border-ink-border bg-ink-raised px-2.5 py-1.5 text-left text-[11px] leading-snug text-mist-muted transition hover:border-accent/40 hover:text-mist"
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
                className={`max-w-[90%] rounded-xl px-2.5 py-1.5 text-xs leading-relaxed ${
                  m.role === "user"
                    ? "ml-auto bg-accent text-white"
                    : "bg-ink-raised text-mist"
                }`}
              >
                {m.content}
              </div>
            ))}

            {busy && (
              <div className="flex w-fit items-center gap-1 rounded-xl bg-ink-raised px-2.5 py-1.5">
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-mist-muted [animation-delay:-0.2s]" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-mist-muted [animation-delay:-0.1s]" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-mist-muted" />
              </div>
            )}

            {error && (
              <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-2.5 py-1.5 text-[11px] text-red-300">
                {error}
              </p>
            )}
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
            className="flex shrink-0 items-center gap-1.5 border-t border-ink-border p-2.5"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask…"
              className="min-w-0 flex-1 rounded-lg border border-ink-border bg-ink-raised px-2.5 py-1.5 text-xs text-mist placeholder:text-mist-muted/60 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
            />
            <button
              type="submit"
              disabled={!input.trim() || busy}
              className="shrink-0 rounded-lg bg-accent px-2.5 py-1.5 text-xs font-semibold text-white transition hover:bg-accent-hover disabled:opacity-50"
            >
              Send
            </button>
          </form>
        </div>
      )}

      <button
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "Close assistant" : "Open assistant"}
        className={`fixed bottom-5 z-50 flex h-12 w-12 items-center justify-center rounded-full bg-accent text-white shadow-lg shadow-accent/30 transition hover:scale-105 hover:bg-accent-hover ${POS}`}
      >
        {open ? (
          <span className="text-lg leading-none">✕</span>
        ) : (
          <span className="text-lg leading-none">✦</span>
        )}
      </button>
    </>
  );
}
