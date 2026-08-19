/**
 * POST /api/ai/analyze
 *
 * Replaces the CLI's old modules/scorer.py + modules/analyzer.py heuristic
 * ranking entirely (see docs/MIGRATION_PLAN.md -- that code is archived,
 * not ported, since real LLM scoring is a strict upgrade over hand-written
 * keyword heuristics). Runs server-side only: GEMINI_API_KEY must never
 * reach the client bundle.
 *
 * Body: { transcript: string, videoTitle?: string }
 * Returns: { summary, viralityScore (0-10), suggestedClips: [{start_hint, end_hint, reason}], tags }
 */

import { NextRequest, NextResponse } from "next/server";
import { GoogleGenAI, Type } from "@google/genai";
import { getSession } from "@/lib/whop-session";

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

const RESPONSE_SCHEMA = {
  type: Type.OBJECT,
  properties: {
    summary: { type: Type.STRING, description: "2-3 sentence summary of the video" },
    viralityScore: { type: Type.NUMBER, description: "0-10 short-form clip potential" },
    tags: { type: Type.ARRAY, items: { type: Type.STRING } },
    suggestedClips: {
      type: Type.ARRAY,
      items: {
        type: Type.OBJECT,
        properties: {
          quote: { type: Type.STRING, description: "The exact line from the transcript this clip starts near" },
          reason: { type: Type.STRING, description: "Why this moment works as a short-form clip" },
        },
        required: ["quote", "reason"],
      },
    },
  },
  required: ["summary", "viralityScore", "tags", "suggestedClips"],
};

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  const { transcript, videoTitle } = await req.json();
  if (!transcript || typeof transcript !== "string") {
    return NextResponse.json({ error: "transcript (string) is required" }, { status: 400 });
  }

  try {
    const response = await ai.models.generateContent({
      model: "gemini-2.5-flash",
      contents: [
        {
          role: "user",
          parts: [{
            text: `Analyze this video transcript${videoTitle ? ` titled "${videoTitle}"` : ""} for short-form clip potential.\n\nTranscript:\n${transcript.slice(0, 20000)}`,
          }],
        },
      ],
      config: {
        responseMimeType: "application/json",
        responseSchema: RESPONSE_SCHEMA,
      },
    });

    const result = JSON.parse(response.text ?? "{}");
    return NextResponse.json(result);
  } catch (e: any) {
    return NextResponse.json({ error: `Gemini analysis failed: ${e.message}` }, { status: 502 });
  }
}
