/**
 * Ported from modules/clip_selector.py:prompt_manual_timestamps()'s
 * duration-bounds check. The UI enforces 5–180 s; this is the server-side
 * belt-and-suspenders so a crafted request cannot ask for a 4-hour clip.
 */

export function validateClipRequest(body: any): string | null {
  if (!body || typeof body !== "object") return "Invalid request body";
  const { url, start, end } = body;
  if (!url || typeof url !== "string") return "url is required";
  if (typeof start !== "number" || typeof end !== "number") {
    return "start and end must be numbers (seconds)";
  }
  if (start < 0 || end <= start) return "end must be greater than start";
  const duration = end - start;
  if (duration < 5) return "Clip must be at least 5 seconds";
  if (duration > 180) return "Clip must be at most 180 seconds";
  return null;
}

export function validateDownloadRequest(body: any): string | null {
  if (!body || typeof body !== "object") return "Invalid request body";
  const { url } = body;
  if (!url || typeof url !== "string") return "url is required";
  // Basic sanity — full URL validation is left to yt-dlp
  if (!/^https?:\/\//i.test(url)) return "url must start with http:// or https://";
  return null;
}

export function validateMetadataRequest(body: any): string | null {
  if (!body || typeof body !== "object") return "Invalid request body";
  const { url } = body;
  if (!url || typeof url !== "string") return "url is required";
  if (!/^https?:\/\//i.test(url)) return "url must start with http:// or https://";
  return null;
}

export function validateTranscriptRequest(body: any): string | null {
  if (!body || typeof body !== "object") return "Invalid request body";
  const { url } = body;
  if (!url || typeof url !== "string") return "url is required";
  if (!/^https?:\/\//i.test(url)) return "url must start with http:// or https://";
  return null;
}
