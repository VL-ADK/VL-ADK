// app/api/tts/route.ts
import { GoogleGenAI } from "@google/genai";
import mime from "mime";
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

const MODEL = "gemini-2.5-pro-preview-tts";

// Map agent names to distinct Gemini prebuilt voices
const AGENT_VOICES = {
    DIRECTOR: "Zephyr",
    PILOT: "Puck",
    OBSERVER: "Vega",
};

const VALID_VOICES = new Set(Object.values(AGENT_VOICES));

export async function POST(req: NextRequest) {
    try {
        const { text, voiceName } = await req.json();

        if (!text || typeof text !== "string") {
            return NextResponse.json(
                { error: "Missing text" },
                { status: 400 }
            );
        }
        const voice =
            typeof voiceName === "string" && VALID_VOICES.has(voiceName)
                ? voiceName
                : "Zephyr"; // default

        const apiKey = process.env.GEMINI_API_KEY;
        if (!apiKey || apiKey === "your_api_key_here") {
            console.warn("TTS disabled: GEMINI_API_KEY not configured");
            return NextResponse.json(
                {
                    error: "TTS disabled: GEMINI_API_KEY not configured. Please set your API key.",
                },
                { status: 503 }
            );
        }

        const ai = new GoogleGenAI({ apiKey });

        // Single-voice config - dynamically choose voice based on agent
        const config = {
            temperature: 1,
            responseModalities: ["audio"],
            speechConfig: {
                voiceConfig: {
                    prebuiltVoiceConfig: { voiceName: voice },
                },
            },
        };

        // We'll stream and concatenate audio chunks (inlineData) into one buffer.
        const contents = [
            {
                role: "user",
                parts: [{ text }], // Just use the text directly, voice is set by config
            },
        ];

        const stream = await ai.models.generateContentStream({
            model: MODEL,
            config,
            contents,
        });

        let mimeType: string | null = null;
        const chunks: Buffer[] = [];

        for await (const chunk of stream) {
            const part = chunk?.candidates?.[0]?.content?.parts?.[0];
            const inline = part?.inlineData;
            if (inline?.data) {
                if (!mimeType && inline?.mimeType) mimeType = inline.mimeType;
                chunks.push(Buffer.from(inline.data, "base64"));
            }
            // If the model emits text logs in between, we just ignore them here.
        }

        if (!chunks.length) {
            return NextResponse.json(
                { error: "No audio produced" },
                { status: 500 }
            );
        }

        // If we didn't get a known mime type, assume wav
        const ext = mimeType ? mime.getExtension(mimeType) || "wav" : "wav";
        const audioBuffer = Buffer.concat(chunks);

        return new NextResponse(audioBuffer, {
            status: 200,
            headers: {
                "Content-Type": mimeType || "audio/wav",
                "Content-Disposition": `inline; filename="agent-tts.${ext}"`,
                "Cache-Control": "no-store",
            },
        });
    } catch (err: any) {
        console.error("[/api/tts] error:", err);

        // Handle quota/rate limit errors specifically
        if (
            err?.status === 429 ||
            err?.message?.includes("quota") ||
            err?.message?.includes("429")
        ) {
            return NextResponse.json(
                {
                    error: "TTS quota exceeded. Please wait or upgrade your Gemini API plan.",
                    type: "quota_exceeded",
                    retryAfter: 60, // seconds
                },
                { status: 429 }
            );
        }

        return NextResponse.json(
            { error: err?.message || "TTS failed" },
            { status: 500 }
        );
    }
}
