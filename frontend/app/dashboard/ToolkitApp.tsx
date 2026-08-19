"use client";

import { useState } from "react";

interface VideoMetadata {
  title: string;
  uploader: string;
  duration: number;
  video_id: string;
  url: string;
  thumbnail?: string;
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
}

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

export default function ToolkitApp() {
  const [url, setUrl] = useState("");
  const [metadata, setMetadata] = useState<VideoMetadata | null>(null);
  const [startInput, setStartInput] = useState("0");
  const [endInput, setEndInput] = useState("30");
  const [format, setFormat] = useState("mp4");
  const [transcript, setTranscript] = useState<TranscriptSegment[] | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  async function fetchMetadata() {
    setError(null);
    setStatus(null);
    setMetadata(null);
    setTranscript(null);
    setAnalysis(null);
    setBusy("metadata");

    try {
      const res = await fetch(`/api/metadata?url=${encodeURIComponent(url)}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to fetch metadata");
      setMetadata(data);
      if (data.duration) {
        setEndInput(String(Math.min(30, Math.floor(data.duration))));
      }
      setStatus(`Loaded: ${data.title}`);
    } catch (e: any) {
      setError(e.message);
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
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || "Clip extraction failed");
      }

      const blob = await res.blob();
      const downloadUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = `clip.${format}`;
      a.click();
      URL.revokeObjectURL(downloadUrl);
      setStatus("Clip downloaded.");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(null);
    }
  }

  async function fetchTranscript() {
    setError(null);
    setStatus(null);
    setTranscript(null);
    setAnalysis(null);
    setBusy("transcript");

    try {
      const res = await fetch("/api/transcript", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Transcript fetch failed");
      setTranscript(data.segments ?? []);
      setStatus(`Transcript loaded (${data.source}).`);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(null);
    }
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
      if (!res.ok) throw new Error(data.error || "Analysis failed");
      setAnalysis(data);
      setStatus("Gemini analysis complete.");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-8">
      <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold mb-4">1. Video URL</h2>
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://youtube.com/watch?v=..."
            className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <button
            onClick={fetchMetadata}
            disabled={!url || busy === "metadata"}
            className="rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
          >
            {busy === "metadata" ? "Loading…" : "Fetch info"}
          </button>
        </div>

        {metadata && (
          <div className="mt-4 flex gap-4 rounded-lg bg-gray-50 p-4">
            {metadata.thumbnail && (
              <img src={metadata.thumbnail} alt="" className="h-20 w-36 rounded object-cover" />
            )}
            <div className="text-sm">
              <p className="font-medium">{metadata.title}</p>
              <p className="text-gray-600">{metadata.uploader}</p>
              {metadata.duration != null && (
                <p className="text-gray-500">Duration: {formatDuration(metadata.duration)}</p>
              )}
            </div>
          </div>
        )}
      </section>

      <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold mb-4">2. Extract clip</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          <label className="block text-sm">
            <span className="mb-1 block text-gray-600">Start (sec or mm:ss)</span>
            <input
              value={startInput}
              onChange={(e) => setStartInput(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2"
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-gray-600">End</span>
            <input
              value={endInput}
              onChange={(e) => setEndInput(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2"
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-gray-600">Format</span>
            <select
              value={format}
              onChange={(e) => setFormat(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2"
            >
              <option value="mp4">mp4</option>
              <option value="mp3">mp3</option>
              <option value="wav">wav</option>
            </select>
          </label>
        </div>
        <button
          onClick={extractClip}
          disabled={!url || !metadata || busy === "clip"}
          className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {busy === "clip" ? "Extracting…" : "Download clip"}
        </button>
        <p className="mt-2 text-xs text-gray-500">Requires the Python backend running on port 8000 with ffmpeg + yt-dlp installed.</p>
      </section>

      <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold mb-4">3. Transcript &amp; AI analysis</h2>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={fetchTranscript}
            disabled={!url || busy === "transcript"}
            className="rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
          >
            {busy === "transcript" ? "Fetching…" : "Get transcript"}
          </button>
          <button
            onClick={analyzeTranscript}
            disabled={!transcript?.length || busy === "analyze"}
            className="rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50"
          >
            {busy === "analyze" ? "Analyzing…" : "Analyze with Gemini"}
          </button>
        </div>

        {transcript && (
          <details className="mt-4">
            <summary className="cursor-pointer text-sm font-medium text-gray-700">
              Transcript preview ({transcript.length} segments)
            </summary>
            <pre className="mt-2 max-h-48 overflow-auto rounded-lg bg-gray-50 p-3 text-xs whitespace-pre-wrap">
              {transcript.map((s) => s.text).join(" ")}
            </pre>
          </details>
        )}

        {analysis && (
          <div className="mt-4 space-y-3 rounded-lg bg-purple-50 p-4 text-sm">
            <p><strong>Summary:</strong> {analysis.summary}</p>
            <p><strong>Virality score:</strong> {analysis.viralityScore}/10</p>
            <p><strong>Tags:</strong> {analysis.tags?.join(", ")}</p>
            {analysis.suggestedClips?.length > 0 && (
              <div>
                <strong>Suggested clips:</strong>
                <ul className="mt-1 list-disc pl-5 space-y-1">
                  {analysis.suggestedClips.map((clip, i) => (
                    <li key={i}>
                      <em>&ldquo;{clip.quote}&rdquo;</em> — {clip.reason}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </section>

      {status && <p className="rounded-lg bg-green-50 px-4 py-3 text-sm text-green-800">{status}</p>}
      {error && <p className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
    </div>
  );
}
