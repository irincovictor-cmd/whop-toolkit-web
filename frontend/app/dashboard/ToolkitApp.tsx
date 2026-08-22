"use client";

import { useState } from "react";
import {
  downloadTextFile,
  safeFilenameBase,
  segmentsToSrt,
  segmentsToTxt,
} from "@/lib/transcript-export";

interface VideoMetadata {
  title: string;
  uploader: string;
  duration: number;
  video_id: string;
  url: string;
  thumbnail?: string;
  platform?: string;
  extractor?: string;
}

interface TranscriptSegment {
  start: number;
  end: number;
  text: string;
}

interface AnalysisResult {
  summary: string;
  viralityScore: number;
  tags: string[];
  suggestedClips: { quote: string; reason: string }[];
  _model?: string;
}

type Aspect = "original" | "portrait" | "landscape";
type FitMode = "letterbox" | "cover";
type Quality = "720" | "1080" | "source";

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function parseTimestamp(value: string): number | null {
  if (!value.trim()) return null;
  if (/^\d+(\.\d+)?$/.test(value)) return parseFloat(value);
  const parts = value.split(":").map(Number);
  if (parts.some(Number.isNaN)) return null;
  if (parts.length === 2) return parts[0] * 60 + parts[1];
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
  return null;
}

function Pill({
  active,
  children,
  onClick,
}: {
  active: boolean;
  children: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
        active
          ? "bg-accent text-white"
          : "border border-ink-border bg-ink-raised text-mist-muted hover:text-mist"
      }`}
    >
      {children}
    </button>
  );
}

export default function ToolkitApp() {
  const [url, setUrl] = useState("");
  const [metadata, setMetadata] = useState<VideoMetadata | null>(null);
  const [startInput, setStartInput] = useState("0:00");
  const [endInput, setEndInput] = useState("0:30");
  const [format, setFormat] = useState("mp4");
  const [aspect, setAspect] = useState<Aspect>("original");
  const [fit, setFit] = useState<FitMode>("cover");
  const [quality, setQuality] = useState<Quality>("1080");
  const [maxMb, setMaxMb] = useState("");
  const [transcript, setTranscript] = useState<TranscriptSegment[] | null>(null);
  const [transcriptMeta, setTranscriptMeta] = useState<{ source?: string } | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  async function fetchMetadata() {
    setError(null);
    setStatus(null);
    setMetadata(null);
    setTranscript(null);
    setTranscriptMeta(null);
    setAnalysis(null);
    setBusy("metadata");

    try {
      const res = await fetch(`/api/metadata?url=${encodeURIComponent(url)}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || data.detail || "Failed to fetch metadata");
      setMetadata(data);
      if (data.duration) {
        setEndInput(formatDuration(Math.min(30, Math.floor(data.duration))));
      }
      const plat = data.platform ? ` · ${data.platform}` : "";
      setStatus(`Loaded: ${data.title}${plat}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to fetch metadata");
    } finally {
      setBusy(null);
    }
  }

  async function downloadFullVideo() {
    setError(null);
    setStatus(null);
    setBusy("download");

    try {
      const res = await fetch("/api/download", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, format }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || data.detail || "Video download failed");
      }

      const blob = await res.blob();
      const downloadUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = `${safeFilenameBase(metadata?.title)}.${format}`;
      a.click();
      URL.revokeObjectURL(downloadUrl);
      setStatus("Full video downloaded to your device.");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Video download failed");
    } finally {
      setBusy(null);
    }
  }

  async function extractClip() {
    setError(null);
    setStatus(null);
    const start = parseTimestamp(startInput);
    const end = parseTimestamp(endInput);
    if (start === null || end === null) {
      setError("Start and end must be seconds or mm:ss / hh:mm:ss.");
      return;
    }

    setBusy("clip");
    try {
      const res = await fetch("/api/clips", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url,
          start,
          end,
          format,
          videoDuration: metadata?.duration,
          aspect,
          fit,
          quality,
          maxMb: maxMb ? Number(maxMb) : undefined,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || data.detail || "Clip extraction failed");
      }

      const blob = await res.blob();
      const downloadUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = `clip.${format}`;
      a.click();
      URL.revokeObjectURL(downloadUrl);
      setStatus("Clip downloaded to your device.");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Clip extraction failed");
    } finally {
      setBusy(null);
    }
  }

  async function fetchTranscript() {
    setError(null);
    setStatus(null);
    setTranscript(null);
    setTranscriptMeta(null);
    setAnalysis(null);
    setBusy("transcript");

    try {
      const res = await fetch("/api/transcript", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || data.detail || "Transcript fetch failed");
      setTranscript(data.segments ?? []);
      setTranscriptMeta({ source: data.source });
      setStatus(
        `Transcript loaded (${data.source}${data.platform ? ` · ${data.platform}` : ""}) — download SRT for CapCut.`
      );
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Transcript fetch failed");
    } finally {
      setBusy(null);
    }
  }

  function downloadSrt() {
    if (!transcript?.length) return;
    const name = `${safeFilenameBase(metadata?.title)}.srt`;
    downloadTextFile(name, segmentsToSrt(transcript), "application/x-subrip");
    setStatus(`Saved ${name} — import as captions in CapCut / Premiere.`);
  }

  function downloadTxt() {
    if (!transcript?.length) return;
    const name = `${safeFilenameBase(metadata?.title)}.txt`;
    downloadTextFile(name, segmentsToTxt(transcript, true), "text/plain");
    setStatus(`Saved ${name}.`);
  }

  async function analyzeTranscript() {
    if (!transcript?.length) {
      setError("Fetch a transcript first.");
      return;
    }

    setError(null);
    setStatus(null);
    setBusy("analyze");

    const fullText = transcript.map((s) => s.text).join(" ");
    try {
      const res = await fetch("/api/ai/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transcript: fullText, videoTitle: metadata?.title }),
      });
      const data = await res.json();
      if (!res.ok) {
        const extra = data.details?.length ? ` (${data.details.join(" | ")})` : "";
        throw new Error((data.error || "Analysis failed") + extra);
      }
      setAnalysis(data);
      setStatus(
        data._model
          ? `Gemini analysis complete (${data._model}).`
          : "Gemini analysis complete."
      );
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setBusy(null);
    }
  }

  const inputClass =
    "w-full rounded-lg border border-ink-border bg-ink-raised px-3 py-2 text-sm text-mist placeholder:text-mist-muted/60 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent";

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <div className="flex flex-col gap-2 rounded-2xl border border-ink-border bg-ink-surface p-2 sm:flex-row sm:items-center">
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Paste YouTube, TikTok, Instagram, X, Vimeo, or Facebook URL…"
          className={`${inputClass} border-0 bg-ink-raised/80 sm:flex-1`}
        />
        <button
          onClick={fetchMetadata}
          disabled={!url || busy === "metadata"}
          className="rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-accent-hover disabled:opacity-50"
        >
          {busy === "metadata" ? "Loading…" : metadata ? "Refresh" : "Fetch info"}
        </button>
      </div>

      {!metadata && !busy && (
        <div className="rounded-2xl border border-dashed border-ink-border bg-ink-surface/50 px-6 py-16 text-center">
          <p className="text-sm font-medium text-mist">Paste a link to get started</p>
          <p className="mt-2 text-xs text-mist-muted">
            Multi-platform via yt-dlp · captions or Whisper for transcript · SRT for CapCut
          </p>
          <div className="mt-4 flex flex-wrap justify-center gap-2">
            {["YouTube", "TikTok", "Instagram", "X", "Vimeo", "Facebook"].map((p) => (
              <span
                key={p}
                className="rounded-full border border-ink-border bg-ink-raised px-3 py-1 text-[11px] text-mist-muted"
              >
                {p}
              </span>
            ))}
          </div>
        </div>
      )}

      {metadata && (
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="space-y-4">
            <section className="overflow-hidden rounded-2xl border border-ink-border bg-ink-surface">
              <div className="aspect-video bg-accent-soft">
                {metadata.thumbnail ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={metadata.thumbnail}
                    alt=""
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <div className="flex h-full items-center justify-center text-xs text-mist-muted">
                    No thumbnail
                  </div>
                )}
              </div>
              <div className="p-4">
                <div className="mb-1 flex flex-wrap items-center gap-2">
                  {metadata.platform && (
                    <span className="rounded-full bg-accent/20 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-accent-hover">
                      {metadata.platform}
                    </span>
                  )}
                </div>
                <h2 className="text-sm font-semibold text-mist">{metadata.title}</h2>
                <p className="mt-1 text-xs text-mist-muted">
                  {metadata.uploader}
                  {metadata.duration != null && <> · {formatDuration(metadata.duration)}</>}
                </p>
                <button
                  onClick={downloadFullVideo}
                  disabled={!url || busy === "download"}
                  className="mt-3 w-full rounded-xl border border-ink-border bg-ink-raised py-2.5 text-sm font-semibold text-mist transition hover:border-accent/40 disabled:opacity-50"
                >
                  {busy === "download" ? "Downloading…" : `Download full video (.${format})`}
                </button>
              </div>
            </section>

            <section className="rounded-2xl border border-ink-border bg-ink-surface p-5">
              <h3 className="mb-4 text-sm font-semibold text-mist">Extract clip</h3>
              <p className="-mt-3 mb-4 text-[11px] text-mist-muted">
                Format below also applies to &ldquo;Download full video&rdquo; above.
              </p>

              <div className="grid grid-cols-3 gap-3">
                <label className="block text-xs text-mist-muted">
                  Start
                  <input
                    value={startInput}
                    onChange={(e) => setStartInput(e.target.value)}
                    className={`${inputClass} mt-1`}
                  />
                </label>
                <label className="block text-xs text-mist-muted">
                  End
                  <input
                    value={endInput}
                    onChange={(e) => setEndInput(e.target.value)}
                    className={`${inputClass} mt-1`}
                  />
                </label>
                <label className="block text-xs text-mist-muted">
                  Format
                  <select
                    value={format}
                    onChange={(e) => setFormat(e.target.value)}
                    className={`${inputClass} mt-1`}
                  >
                    <option value="mp4">mp4</option>
                    <option value="mp3">mp3</option>
                    <option value="wav">wav</option>
                  </select>
                </label>
              </div>

              <div className="mt-4">
                <p className="mb-2 text-xs text-mist-muted">Aspect</p>
                <div className="flex flex-wrap gap-2">
                  <Pill active={aspect === "original"} onClick={() => setAspect("original")}>
                    Original
                  </Pill>
                  <Pill active={aspect === "portrait"} onClick={() => setAspect("portrait")}>
                    Portrait 9:16
                  </Pill>
                  <Pill active={aspect === "landscape"} onClick={() => setAspect("landscape")}>
                    Landscape 16:9
                  </Pill>
                </div>
              </div>

              <div className="mt-4">
                <p className="mb-2 text-xs text-mist-muted">Fit mode</p>
                <div className="flex flex-wrap gap-2">
                  <Pill active={fit === "letterbox"} onClick={() => setFit("letterbox")}>
                    Letterbox
                  </Pill>
                  <Pill active={fit === "cover"} onClick={() => setFit("cover")}>
                    Cover (zoom fill)
                  </Pill>
                </div>
              </div>

              <div className="mt-4">
                <p className="mb-2 text-xs text-mist-muted">Quality / max height</p>
                <div className="flex flex-wrap gap-2">
                  <Pill active={quality === "720"} onClick={() => setQuality("720")}>
                    720p
                  </Pill>
                  <Pill active={quality === "1080"} onClick={() => setQuality("1080")}>
                    1080p
                  </Pill>
                  <Pill active={quality === "source"} onClick={() => setQuality("source")}>
                    Source
                  </Pill>
                </div>
              </div>

              <div className="mt-4">
                <label className="block text-xs text-mist-muted">
                  Max file size (optional, MB)
                  <input
                    value={maxMb}
                    onChange={(e) => setMaxMb(e.target.value)}
                    placeholder="e.g. 50"
                    className={`${inputClass} mt-1 max-w-[8rem]`}
                  />
                </label>
              </div>

              <button
                onClick={extractClip}
                disabled={!url || !metadata || busy === "clip"}
                className="mt-5 w-full rounded-xl bg-accent py-3 text-sm font-semibold text-white transition hover:bg-accent-hover disabled:opacity-50"
              >
                {busy === "clip" ? "Extracting…" : "Download clip"}
              </button>
            </section>
          </div>

          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              <button
                onClick={fetchTranscript}
                disabled={!url || busy === "transcript"}
                className="rounded-xl border border-ink-border bg-ink-raised px-4 py-2.5 text-sm font-semibold text-mist transition hover:bg-accent/40 disabled:opacity-50"
              >
                {busy === "transcript" ? "Fetching…" : "Get transcript"}
              </button>
              <button
                onClick={analyzeTranscript}
                disabled={!transcript?.length || busy === "analyze"}
                className="rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-accent-hover disabled:opacity-50"
              >
                {busy === "analyze" ? "Analyzing…" : "Analyze with Gemini"}
              </button>
            </div>

            <section className="rounded-2xl border border-ink-border bg-ink-surface p-5">
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-semibold text-mist">
                  Transcript
                  {transcriptMeta?.source ? (
                    <span className="ml-2 text-[11px] font-normal text-mist-muted">
                      · {transcriptMeta.source}
                    </span>
                  ) : null}
                </h3>
                {transcript && transcript.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={downloadSrt}
                      className="rounded-lg border border-ink-border bg-ink-raised px-2.5 py-1 text-[11px] font-semibold text-mist hover:border-accent/50"
                    >
                      Download .srt
                    </button>
                    <button
                      type="button"
                      onClick={downloadTxt}
                      className="rounded-lg border border-ink-border bg-ink-raised px-2.5 py-1 text-[11px] font-semibold text-mist hover:border-accent/50"
                    >
                      Download .txt
                    </button>
                  </div>
                )}
              </div>
              <p className="mb-2 text-[11px] text-mist-muted">
                .srt has timestamps (CapCut: Captions → Import). Timed to each line start/end.
              </p>
              {transcript ? (
                <div className="scroll-dark max-h-48 overflow-auto text-xs leading-relaxed text-mist-muted">
                  {transcript.map((s, i) => (
                    <p key={i} className="mb-1">
                      <span className="text-mist-muted/70">
                        [{formatDuration(s.start)}]
                      </span>{" "}
                      {s.text}
                    </p>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-mist-muted">No transcript yet.</p>
              )}
            </section>

            <section className="rounded-2xl border border-accent/30 bg-accent-soft p-5">
              <div className="mb-3 flex items-center gap-2">
                <h3 className="text-sm font-semibold text-mist">Gemini analysis</h3>
                {analysis && (
                  <span className="rounded-full bg-accent px-2 py-0.5 text-[11px] font-semibold text-white">
                    {analysis.viralityScore} / 10
                  </span>
                )}
              </div>

              {!analysis && (
                <p className="text-xs text-mist-muted">
                  Needs GEMINI_API_KEY in frontend/.env.local. If one model fails, the API tries
                  fallbacks automatically.
                </p>
              )}

              {analysis && (
                <div className="space-y-4 text-sm">
                  <div>
                    <p className="text-[11px] font-medium uppercase tracking-wide text-mist-muted">
                      Summary
                    </p>
                    <p className="mt-1 text-mist">{analysis.summary}</p>
                  </div>
                  {analysis.tags?.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {analysis.tags.map((t) => (
                        <span
                          key={t}
                          className="rounded-full border border-ink-border bg-ink-surface px-2 py-0.5 text-[11px] text-mist-muted"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                  {analysis.suggestedClips?.length > 0 && (
                    <div>
                      <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-mist-muted">
                        Suggested clips
                      </p>
                      <ul className="space-y-2">
                        {analysis.suggestedClips.map((clip, i) => (
                          <li
                            key={i}
                            className="rounded-xl border border-ink-border/60 bg-ink-surface px-3 py-2"
                          >
                            <p className="text-xs font-semibold text-mist">
                              &ldquo;{clip.quote}&rdquo;
                            </p>
                            <p className="mt-0.5 text-[11px] text-mist-muted">{clip.reason}</p>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </section>
          </div>
        </div>
      )}

      {status && (
        <p className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">
          {status}
        </p>
      )}
      {error && (
        <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </p>
      )}
    </div>
  );
}
