/**
 * POST /api/ai/analyze
 *
 * Gemini analysis with model fallbacks (quota / model-id churn is common).
 * Body: { transcript: string, videoTitle?: string }
 */

import { NextRequest, NextResponse } from "next/server";
import { GoogleGenAI, Type } from "@google/genai";
import { getSession } from "@/lib/whop-session";

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
          quote: {
            type: Type.STRING,
            description: "Exact line from the transcript this clip starts near",
          },
          reason: {
            type: Type.STRING,
            description: "Why this moment works as a short-form clip",
          },
        },
        required: ["quote", "reason"],
      },
    },
  },
  required: ["summary", "viralityScore", "tags", "suggestedClips"],
};

// Prefer flash models; fall back if one id is retired or quota-blocked.
const MODEL_CANDIDATES = [
  "gemini-2.5-flash",
  "gemini-2.0-flash",
  "gemini-1.5-flash",
  "gemini-flash-latest",
];

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  const apiKey = process.env.GEMINI_API_KEY?.trim();
  if (!apiKey) {
    return NextResponse.json(
      {
        error:
          "GEMINI_API_KEY is missing. Set it in frontend/.env.local and restart npm run dev.",
      },
      { status: 503 }
    );
  }

  const { transcript, videoTitle } = await req.json();
  if (!transcript || typeof transcript !== "string") {
    return NextResponse.json({ error: "transcript (string) is required" }, { status: 400 });
  }

  const ai = new GoogleGenAI({ apiKey });
  const prompt = `Analyze this video transcript${
    videoTitle ? ` titled "${videoTitle}"` : ""
  } for short-form clip potential.\n\nTranscript:\n${transcript.slice(0, 20000)}`;

  const errors: string[] = [];

  for (const model of MODEL_CANDIDATES) {
    try {
      const response = await ai.models.generateContent({
        model,
        contents: [{ role: "user", parts: [{ text: prompt }] }],
        config: {
          responseMimeType: "application/json",
          responseSchema: RESPONSE_SCHEMA,
        },
      });

      const raw = response.text ?? "{}";
      const result = JSON.parse(raw);
      return NextResponse.json({ ...result, _model: model });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      errors.push(`${model}: ${msg}`);
      // Try next model on not-found / overload / rate limit style failures
      const retryable =
        /404|not found|429|quota|resource.exhausted|overloaded|503|unavailable/i.test(msg);
      if (!retryable) {
        return NextResponse.json(
          { error: `Gemini analysis failed: ${msg}` },
          { status: 502 }
        );
      }
    }
  }

  return NextResponse.json(
    {
      error:
        "Gemini analysis failed on all models. Check API key, billing/quota, and model access.",
      details: errors.slice(-4),
    },
    { status: 502 }
  );
}
