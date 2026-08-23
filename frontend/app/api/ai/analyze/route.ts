/**
 * POST /api/ai/analyze
 *
 * Gemini analysis with model fallbacks (quota / model-id churn is common).
 * Body: { transcript: string, videoTitle?: string }
 *
 * Returns a creator-assistant style brief: overall virality, ranked clip
 * ideas with start/end timestamps, editing style tips, and hashtags.
 */

import { NextRequest, NextResponse } from "next/server";
import { GoogleGenAI, Type } from "@google/genai";
import { getSession } from "@/lib/whop-session";

const RESPONSE_SCHEMA = {
  type: Type.OBJECT,
  properties: {
    summary: {
      type: Type.STRING,
      description: "2-4 sentence overview of the video and what works for short-form",
    },
    viralityScore: {
      type: Type.NUMBER,
      description: "0-10 overall short-form potential for this source",
    },
    overallStrategy: {
      type: Type.STRING,
      description:
        "Practical advice for the creator: what to prioritize, platform fit, hook strategy",
    },
    tags: {
      type: Type.ARRAY,
      items: { type: Type.STRING },
      description: "Topic / theme tags (not hashtags)",
    },
    hashtags: {
      type: Type.ARRAY,
      items: { type: Type.STRING },
      description: "Ready-to-paste hashtags including the # symbol, 8-15 items",
    },
    editingAdvice: {
      type: Type.STRING,
      description:
        "Concrete editing style guidance (pacing, captions, cuts, B-roll, music, text on screen)",
    },
    suggestedClips: {
      type: Type.ARRAY,
      items: {
        type: Type.OBJECT,
        properties: {
          rank: {
            type: Type.NUMBER,
            description: "1 = best clip idea, then 2, 3, ...",
          },
          score: {
            type: Type.NUMBER,
            description: "0-10 how strong this specific clip is",
          },
          startSeconds: {
            type: Type.NUMBER,
            description: "Clip start time in seconds from the transcript timestamps",
          },
          endSeconds: {
            type: Type.NUMBER,
            description: "Clip end time in seconds (typically 15-60s long)",
          },
          startLabel: {
            type: Type.STRING,
            description: "Human timestamp e.g. 1:24",
          },
          endLabel: {
            type: Type.STRING,
            description: "Human timestamp e.g. 1:52",
          },
          quote: {
            type: Type.STRING,
            description: "Key line or hook from that section of the transcript",
          },
          reason: {
            type: Type.STRING,
            description: "Why this moment works as a short-form clip",
          },
          editingStyle: {
            type: Type.STRING,
            description:
              "How to edit this clip (cuts, captions, zoom, music mood, text overlay)",
          },
        },
        required: [
          "rank",
          "score",
          "startSeconds",
          "endSeconds",
          "startLabel",
          "endLabel",
          "quote",
          "reason",
          "editingStyle",
        ],
      },
    },
  },
  required: [
    "summary",
    "viralityScore",
    "overallStrategy",
    "tags",
    "hashtags",
    "editingAdvice",
    "suggestedClips",
  ],
};

const MODEL_CANDIDATES = [
  "gemini-3.6-flash",
  "gemini-3.7-flash",
  "gemini-3.5-flash-lite",
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
  const prompt = `You are a short-form content assistant for creators using Whop Toolkit.
Help the user decide which moments to clip, how to edit them, and how to post them.

Video title: ${videoTitle ? `"${videoTitle}"` : "(unknown)"}

The transcript below includes [start-end] timestamps in mm:ss (or m:ss). Use those times.
Suggest 3-6 clips ranked best-first. Each clip should usually be 15-45 seconds.
startSeconds/endSeconds must match the transcript timestamps as closely as possible.
hashtags must include the # character.
editingStyle and editingAdvice must be concrete and actionable (not vague).

Timed transcript:
${transcript.slice(0, 28000)}`;

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

      // Ensure clips are sorted by rank ascending
      if (Array.isArray(result.suggestedClips)) {
        result.suggestedClips.sort(
          (a: { rank?: number }, b: { rank?: number }) => (a.rank ?? 99) - (b.rank ?? 99)
        );
      }

      return NextResponse.json({ ...result, _model: model });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      errors.push(`${model}: ${msg}`);
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
