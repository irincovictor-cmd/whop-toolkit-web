/**
 * Ported from modules/clip_selector.py:prompt_manual_timestamps()'s
 * duration-bounds check. That logic was already correct -- reject a
 * start/end that falls outside [0, video_duration] before it ever
 * reaches ffmpeg -- so this is a direct translation, not a rewrite.
 */

interface ClipRequestBody {
  url?: string;
  start?: number;
  end?: number;
  format?: string;
  videoDuration?: number; // optional: pass this from the /metadata call for tighter validation
}

export function validateClipRequest(body: ClipRequestBody): string | null {
  if (!body.url || typeof body.url !== "string") {
    return "A video URL is required.";
  }
  if (typeof body.start !== "number" || typeof body.end !== "number") {
    return "start and end must be numbers (seconds).";
  }
  if (body.start < 0) {
    return "start can't be negative.";
  }
  if (body.end <= body.start) {
    return "end must be after start.";
  }
  if (body.videoDuration && body.end > body.videoDuration) {
    return `This video is only ${Math.floor(body.videoDuration)}s long -- both timestamps must fall within that.`;
  }
  if (body.format && !["mp4", "mp3", "wav"].includes(body.format)) {
    return `Unsupported format: ${body.format}`;
  }
  return null;
}
