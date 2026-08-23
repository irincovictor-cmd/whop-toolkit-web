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
type Mode = "download" | "clip" | "transcript" | "analyze";

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
          ? "bg-accent text-white shadow-sm"
          : "border border-ink-border bg-ink-raised text-mist-muted hover:border-accent/40 hover:text-mist"
      }`}
    >
      {children}
    </button>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-mist-muted">
      {children}
    </p>
  );
}

const MODES: { id: Mode; label: string; hint: string }[] = [
  { id: "download", label: "Download", hint: "Full video" },
  { id: "clip", label: "Clip", hint: "Cut a section" },
  { id: "transcript", label: "Transcript", hint: "Captions & SRT" },
  { id: "analyze", label: "Analyze", hint: "Gemini insights" },
];

export default function ToolkitApp() {
  const [url, setUrl] = useState("");
  const [metadata, setMetadata] = useState<VideoMetadata | null>(null);
  const [mode, setMode] = useState<Mode>("download");
  const [startInput, setStartInput] = useState("0:00");
  const [endInput, setEndInput] = useState("0:30");
  const [format, setFormat] = useState("mp4");
  const [aspect, setAspect] = useState<Aspect>("original");
  const [fit, setFit] = useState<FitMode>("cover");
  const [quality, setQuality] = useState<Quality>("1080");
  const [maxMb, setMaxMb] = useState("");
  const [transcript, setTranscript] = useState<TranscriptSegment[] | null>(null);
  const [transcriptMeta, setTranscriptMeta] = useState<{ source?: string } | null>(null);
  const [localFile, setLocalFile] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const inputClass =
    "w-full rounded-xl border border-ink-border bg-ink-raised px-3.5 py-2.5 text-sm text-mist placeholder:text-mist-muted/50 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/60";

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
      if (data.duration) setEndInput(formatDuration(Math.min(30, Math.floor(data.duration))));
      const plat = data.platform ? ` · ${data.platform}` : "";
      setStatus(`Loaded: ${data.title}${plat}`);
      setMode("download");
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
      const qualityLabel = res.headers.get("X-Video-Quality");
      const qualityTag = qualityLabel ? ` (${qualityLabel})` : "";
      const downloadUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = `${safeFilenameBase(metadata?.title)}${qualityTag}.${format}`;
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
      const qualityLabel = res.headers.get("X-Video-Quality");
      const qualityTag = qualityLabel ? ` (${qualityLabel})` : "";
      const downloadUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = `${safeFilenameBase(metadata?.title || "video")}_${Math.floor(start)}s-${Math.floor(end)}s${qualityTag}.${format}`;
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
      setStatus(`Transcript loaded (${data.source}${data.platform ? ` · ${data.platform}` : ""}) — download SRT for CapCut.`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Transcript fetch failed");
    } finally {
      setBusy(null);
    }
  }

  async function fetchTranscriptFromFile() {
    if (!localFile) {
      setError("Choose a video file first.");
      return;
    }
    setError(null);
    setStatus(null);
    setTranscript(null);
    setTranscriptMeta(null);
    setAnalysis(null);
    setBusy("transcript-local");
    try {
      const form = new FormData();
      form.append("file", localFile);
      form.append("whisper_model", "base");
      const res = await fetch("/api/transcript/local", { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || data.detail || "Local transcript failed");
      setTranscript(data.segments ?? []);
      setTranscriptMeta({ source: data.source });
      setStatus(`Transcript loaded from ${localFile.name} (Whisper) — download SRT for CapCut.`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Local transcript failed");
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
      setError("Fetch a transcript first (Transcript tab).");
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
      setStatus(data._model ? `Gemini analysis complete (${data._model}).` : "Gemini analysis complete.");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-8">
      <div className="rounded-2xl border border-ink-border bg-ink-surface p-2 shadow-glow/30">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && url && !busy && fetchMetadata()}
            placeholder="Paste YouTube, TikTok, Instagram, X, Vimeo, or Facebook URL…"
            className={`${inputClass} border-0 bg-transparent sm:flex-1`}
          />
          <button
            onClick={fetchMetadata}
            disabled={!url || busy === "metadata"}
            className="shrink-0 rounded-xl bg-accent px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-accent-hover disabled:opacity-50"
          >
            {busy === "metadata" ? "Loading…" : metadata ? "Refresh" : "Fetch info"}
          </button>
        </div>
      </div>

      {!metadata && !busy && (
        <div className="rounded-2xl border border-dashed border-ink-border bg-ink-surface/40 px-6 py-16 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-accent/15 text-accent">
            <span className="text-xl">▶</span>
          </div>
          <p className="text-base font-semibold text-mist">Paste a link to get started</p>
          <p className="mt-2 text-sm text-mist-muted">
            Multi-platform via yt-dlp · captions or Whisper · SRT for CapCut
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-2">
            {["YouTube", "TikTok", "Instagram", "X", "Vimeo", "Facebook"].map((p) => (
              <span key={p} className="rounded-full border border-ink-border bg-ink-raised px-3 py-1 text-[11px] text-mist-muted">{p}</span>
            ))}
          </div>
        </div>
      )}

      {metadata && (
        <>
          <div className="overflow-hidden rounded-2xl border border-ink-border bg-ink-surface">
            <div className="flex flex-col sm:flex-row">
              <div className="aspect-video w-full shrink-0 bg-accent-soft sm:w-56 sm:aspect-auto sm:self-stretch">
                {metadata.thumbnail ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={metadata.thumbnail} alt="" className="h-full w-full object-cover" />
                ) : (
                  <div className="flex h-full min-h-[8rem] items-center justify-center text-xs text-mist-muted">No thumbnail</div>
                )}
              </div>
              <div className="flex flex-1 flex-col justify-center gap-2 p-5">
                <div className="flex flex-wrap items-center gap-2">
                  {metadata.platform && (
                    <span className="rounded-full bg-accent/20 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-accent-hover">{metadata.platform}</span>
                  )}
                  {metadata.duration != null && (
                    <span className="text-xs text-mist-muted">{formatDuration(metadata.duration)}</span>
                  )}
                </div>
                <h2 className="text-base font-semibold leading-snug text-mist line-clamp-2">{metadata.title}</h2>
                <p className="text-sm text-mist-muted">{metadata.uploader}</p>
              </div>
            </div>
          </div>

          <div className="flex gap-1 overflow-x-auto rounded-2xl border border-ink-border bg-ink-surface p-1.5">
            {MODES.map((m) => (
              <button
                key={m.id}
                onClick={() => setMode(m.id)}
                className={`flex min-w-0 flex-1 flex-col items-center rounded-xl px-3 py-2.5 text-center transition ${
                  mode === m.id ? "bg-accent text-white shadow-sm" : "text-mist-muted hover:bg-ink-raised hover:text-mist"
                }`}
              >
                <span className="text-sm font-semibold">{m.label}</span>
                <span className={`mt-0.5 hidden text-[10px] sm:block ${mode === m.id ? "text-white/70" : "text-mist-muted/70"}`}>{m.hint}</span>
              </button>
            ))}
          </div>

          <div className="rounded-2xl border border-ink-border bg-ink-surface p-6">
            {mode === "download" && (
              <div className="mx-auto max-w-md space-y-6">
                <div>
                  <h3 className="text-lg font-semibold text-mist">Download full video</h3>
                  <p className="mt-1 text-sm text-mist-muted">Grab the entire file. Same format setting is used for clips.</p>
                </div>
                <div>
                  <SectionLabel>Format</SectionLabel>
                  <div className="flex flex-wrap gap-2">
                    {(["mp4", "mp3", "wav"] as const).map((f) => (
                      <Pill key={f} active={format === f} onClick={() => setFormat(f)}>.{f}</Pill>
                    ))}
                  </div>
                </div>
                <button onClick={downloadFullVideo} disabled={!url || busy === "download"} className="w-full rounded-xl bg-accent py-3.5 text-sm font-semibold text-white transition hover:bg-accent-hover disabled:opacity-50">
                  {busy === "download" ? "Downloading…" : `Download full video (.${format})`}
                </button>
              </div>
            )}

            {mode === "clip" && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold text-mist">Extract clip</h3>
                  <p className="mt-1 text-sm text-mist-muted">Cut a timestamped section. Aspect / fit / quality apply here only.</p>
                </div>
                <div className="grid gap-4 sm:grid-cols-3">
                  <label className="block text-xs text-mist-muted">Start<input value={startInput} onChange={(e) => setStartInput(e.target.value)} placeholder="0:00" className={`${inputClass} mt-1.5`} /></label>
                  <label className="block text-xs text-mist-muted">End<input value={endInput} onChange={(e) => setEndInput(e.target.value)} placeholder="0:30" className={`${inputClass} mt-1.5`} /></label>
                  <label className="block text-xs text-mist-muted">Format<select value={format} onChange={(e) => setFormat(e.target.value)} className={`${inputClass} mt-1.5`}><option value="mp4">mp4</option><option value="mp3">mp3</option><option value="wav">wav</option></select></label>
                </div>
                <div className="grid gap-6 sm:grid-cols-2">
                  <div><SectionLabel>Aspect</SectionLabel><div className="flex flex-wrap gap-1.5"><Pill active={aspect === "original"} onClick={() => setAspect("original")}>Original</Pill><Pill active={aspect === "portrait"} onClick={() => setAspect("portrait")}>9:16 Portrait</Pill><Pill active={aspect === "landscape"} onClick={() => setAspect("landscape")}>16:9 Landscape</Pill></div></div>
                  <div><SectionLabel>Fit mode</SectionLabel><div className="flex flex-wrap gap-1.5"><Pill active={fit === "letterbox"} onClick={() => setFit("letterbox")}>Letterbox</Pill><Pill active={fit === "cover"} onClick={() => setFit("cover")}>Cover (zoom)</Pill></div></div>
                  <div><SectionLabel>Quality</SectionLabel><div className="flex flex-wrap gap-1.5"><Pill active={quality === "720"} onClick={() => setQuality("720")}>720p</Pill><Pill active={quality === "1080"} onClick={() => setQuality("1080")}>1080p</Pill><Pill active={quality === "source"} onClick={() => setQuality("source")}>Source</Pill></div></div>
                  <div><SectionLabel>Max size (MB, optional)</SectionLabel><input value={maxMb} onChange={(e) => setMaxMb(e.target.value)} placeholder="e.g. 50" className={`${inputClass} max-w-[10rem]`} /></div>
                </div>
                <button onClick={extractClip} disabled={!url || !metadata || busy === "clip"} className="w-full rounded-xl bg-accent py-3.5 text-sm font-semibold text-white transition hover:bg-accent-hover disabled:opacity-50 sm:w-auto sm:px-10">
                  {busy === "clip" ? "Extracting…" : "Download clip"}
                </button>
              </div>
            )}

            {mode === "transcript" && (
              <div className="space-y-5">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-mist">Transcript</h3>
                    <p className="mt-1 text-sm text-mist-muted">YouTube captions when available, otherwise Whisper. Export .srt for CapCut.</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button onClick={fetchTranscript} disabled={!url || busy === "transcript"} className="rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-accent-hover disabled:opacity-50">
                      {busy === "transcript" ? "Fetching…" : transcript ? "Refresh transcript" : "Get transcript"}
                    </button>
                    {transcript && transcript.length > 0 && (
                      <>
                        <button type="button" onClick={downloadSrt} className="rounded-xl border border-ink-border bg-ink-raised px-4 py-2.5 text-sm font-semibold text-mist transition hover:border-accent/40">.srt</button>
                        <button type="button" onClick={downloadTxt} className="rounded-xl border border-ink-border bg-ink-raised px-4 py-2.5 text-sm font-semibold text-mist transition hover:border-accent/40">.txt</button>
                      </>
                    )}
                  </div>
                </div>
                {transcriptMeta?.source && (<p className="text-xs text-mist-muted">Source: <span className="text-mist">{transcriptMeta.source}</span></p>)}
                <div className="flex flex-col gap-2 rounded-xl border border-dashed border-ink-border p-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-mist-muted">Or transcribe a video already on your device:</span>
                    <input
                      type="file"
                      accept="video/*,audio/*"
                      onChange={(e) => setLocalFile(e.target.files?.[0] ?? null)}
                      className="text-xs text-mist-muted file:mr-2 file:rounded-lg file:border-0 file:bg-ink-raised file:px-3 file:py-1.5 file:text-xs file:font-semibold file:text-mist hover:file:border-accent/40"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={fetchTranscriptFromFile}
                    disabled={!localFile || busy === "transcript-local"}
                    className="rounded-xl border border-ink-border bg-ink-raised px-4 py-2 text-xs font-semibold text-mist transition hover:border-accent/40 disabled:opacity-50"
                  >
                    {busy === "transcript-local" ? "Transcribing…" : "Transcribe file"}
                  </button>
                </div>
                {transcript ? (
                  <div className="scroll-dark max-h-[28rem] overflow-auto rounded-xl border border-ink-border bg-ink-raised/50 p-4 text-sm leading-relaxed text-mist-muted">
                    {transcript.map((s, i) => (
                      <p key={i} className="mb-2 last:mb-0">
                        <span className="mr-2 inline-block min-w-[3rem] font-mono text-[11px] text-mist-muted/60">{formatDuration(s.start)}</span>
                        {s.text}
                      </p>
                    ))}
                  </div>
                ) : (
                  <div className="rounded-xl border border-dashed border-ink-border px-6 py-12 text-center text-sm text-mist-muted">No transcript yet. Click “Get transcript” above.</div>
                )}
              </div>
            )}

            {mode === "analyze" && (
              <div className="space-y-5">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-mist">Gemini analysis</h3>
                    <p className="mt-1 text-sm text-mist-muted">Virality score, tags, and suggested clip hooks. Requires a transcript first.</p>
                  </div>
                  <button onClick={analyzeTranscript} disabled={!transcript?.length || busy === "analyze"} className="rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-accent-hover disabled:opacity-50">
                    {busy === "analyze" ? "Analyzing…" : "Run analysis"}
                  </button>
                </div>
                {!transcript?.length && !analysis && (
                  <div className="rounded-xl border border-dashed border-ink-border px-6 py-12 text-center text-sm text-mist-muted">
                    Switch to the <button type="button" onClick={() => setMode("transcript")} className="font-semibold text-accent hover:underline">Transcript</button> tab and fetch captions first.
                  </div>
                )}
                {transcript?.length && !analysis && busy !== "analyze" && (
                  <div className="rounded-xl border border-ink-border bg-ink-raised/40 px-6 py-10 text-center text-sm text-mist-muted">Transcript ready ({transcript.length} segments). Click “Run analysis”.</div>
                )}
                {analysis && (
                  <div className="space-y-6">
                    <div className="flex items-center gap-3">
                      <span className="rounded-full bg-accent px-3 py-1 text-sm font-bold text-white">{analysis.viralityScore} / 10</span>
                      <span className="text-sm text-mist-muted">Virality score</span>
                    </div>
                    <div><SectionLabel>Summary</SectionLabel><p className="text-sm leading-relaxed text-mist">{analysis.summary}</p></div>
                    {analysis.tags?.length > 0 && (
                      <div><SectionLabel>Tags</SectionLabel><div className="flex flex-wrap gap-1.5">{analysis.tags.map((t) => (<span key={t} className="rounded-full border border-ink-border bg-ink-raised px-2.5 py-1 text-[11px] text-mist-muted">{t}</span>))}</div></div>
                    )}
                    {analysis.suggestedClips?.length > 0 && (
                      <div><SectionLabel>Suggested clips</SectionLabel><ul className="space-y-3">{analysis.suggestedClips.map((clip, i) => (<li key={i} className="rounded-xl border border-ink-border bg-ink-raised px-4 py-3"><p className="text-sm font-semibold text-mist">&ldquo;{clip.quote}&rdquo;</p><p className="mt-1 text-xs leading-relaxed text-mist-muted">{clip.reason}</p></li>))}</ul></div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </>
      )}

      {status && (<p className="rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">{status}</p>)}
      {error && (<p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</p>)}
    </div>
  );
}
