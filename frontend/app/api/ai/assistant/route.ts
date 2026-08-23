/**
 * POST /api/ai/assistant
 *
 * Conversational helper widget (see components/AiHelper.tsx) -- distinct
 * from /api/ai/analyze, which does one-shot structured transcript analysis.
 */

import { NextRequest, NextResponse } from "next/server";
import { GoogleGenAI } from "@google/genai";
import { getSession } from "@/lib/whop-session";

const MODEL_CANDIDATES = ["gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.5-flash-lite"];

const SYSTEM_PROMPT = `You are the in-app helper for Whop Toolkit, a web tool creators use to:
- paste a YouTube/TikTok/Instagram/X/Facebook/Vimeo URL
- extract timestamped clips (aspect ratio, fit mode, quality, max file size)
- download full videos
- fetch/export transcripts as .srt or .txt
- run Gemini analysis on a transcript for virality scoring and clip suggestions

Your job is to help users with two kinds of questions:
1. How to use this app -- where a control lives, what a setting does, why
   something might have failed (e.g. quality drops, unsupported platform).
2. General creator knowledge in this app's lane: short-form video editing,
   trimming/pacing, audio and music selection and mixing, sound design for
   clips, aspect ratios and platform specs, short-form trends and hook
   writing, and how Whop (the creator commerce platform this tool is built
   for) works for selling access to content/communities.

Stay in that lane. If asked something clearly outside it (general coding
help unrelated to this app, unrelated trivia, other unrelated products),
say briefly that it's outside what you help with here and redirect back to
video/audio/clips/trends/Whop topics -- don't just refuse silently.

Be concise and concrete. Prefer short, direct answers over long essays;
use steps only when the user needs to actually do a sequence of things.
Never invent app features that don't exist in the list above.

IMPORTANT: Reply in plain text only. Do not use markdown, asterisks for bold,
bullet markers with stars, code fences, or any formatting symbols. Write
normal sentences and numbered lists like 1. 2. 3. if needed.`;

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  const apiKey = process.env.GEMINI_API_KEY?.trim();
  if (!apiKey) {
    return NextResponse.json(
      { error: "GEMINI_API_KEY is missing. Set it in frontend/.env.local and restart npm run dev." },
      { status: 503 }
    );
  }

  const { messages } = (await req.json()) as { messages?: ChatMessage[] };
  if (!Array.isArray(messages) || messages.length === 0) {
    return NextResponse.json({ error: "messages (non-empty array) is required" }, { status: 400 });
  }

  const recent = messages.slice(-20);
  const contents = recent.map((m) => ({
    role: m.role === "assistant" ? "model" : "user",
    parts: [{ text: m.content }],
  }));

  const ai = new GoogleGenAI({ apiKey });
  const errors: string[] = [];

  for (const model of MODEL_CANDIDATES) {
    try {
      const response = await ai.models.generateContent({
        model,
        contents,
        config: { systemInstruction: SYSTEM_PROMPT },
      });
      const reply = response.text ?? "";
      return NextResponse.json({ reply, _model: model });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      errors.push(`${model}: ${msg}`);
      const retryable = /404|not found|429|quota|resource.exhausted|overloaded|503|unavailable/i.test(msg);
      if (!retryable) {
        return NextResponse.json({ error: `Assistant failed: ${msg}` }, { status: 502 });
      }
    }
  }

  return NextResponse.json(
    { error: "Assistant failed on all models.", details: errors.slice(-3) },
    { status: 502 }
  );
}
