/** Build CapCut / Premiere-friendly subtitle + plain text from timed segments. */

export interface TimedSegment {
  start: number;
  end: number;
  text: string;
}

/** SRT timestamp: HH:MM:SS,mmm */
export function toSrtTime(seconds: number): string {
  const totalMs = Math.max(0, Math.round(seconds * 1000));
  const h = Math.floor(totalMs / 3_600_000);
  const m = Math.floor((totalMs % 3_600_000) / 60_000);
  const s = Math.floor((totalMs % 60_000) / 1000);
  const ms = totalMs % 1000;
  return (
    `${String(h).padStart(2, "0")}:` +
    `${String(m).padStart(2, "0")}:` +
    `${String(s).padStart(2, "0")},` +
    `${String(ms).padStart(3, "0")}`
  );
}

/** Standard SubRip (.srt) — import into CapCut, Premiere, DaVinci, etc. */
export function segmentsToSrt(segments: TimedSegment[]): string {
  return segments
    .map((seg, i) => {
      const text = (seg.text || "").trim().replace(/\r?\n/g, " ");
      return `${i + 1}\n${toSrtTime(seg.start)} --> ${toSrtTime(seg.end)}\n${text}\n`;
    })
    .join("\n");
}

/** Plain text with optional [mm:ss] prefixes for reference. */
export function segmentsToTxt(segments: TimedSegment[], withTimestamps = true): string {
  if (!withTimestamps) {
    return segments.map((s) => (s.text || "").trim()).filter(Boolean).join("\n");
  }
  return segments
    .map((s) => {
      const m = Math.floor(s.start / 60);
      const sec = Math.floor(s.start % 60);
      const stamp = `${m}:${String(sec).padStart(2, "0")}`;
      return `[${stamp}] ${(s.text || "").trim()}`;
    })
    .filter((line) => line.length > 3)
    .join("\n");
}

export function downloadTextFile(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: `${mime};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function safeFilenameBase(title?: string): string {
  const base = (title || "transcript").replace(/[^\w\s-]+/g, "").trim().slice(0, 60);
  return base || "transcript";
}
