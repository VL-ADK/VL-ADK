"use client";

import { Loader, Mic, MicOff, Send, Volume2, VolumeX } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import SpeechRecognition, {
    useSpeechRecognition,
} from "react-speech-recognition";
import { sendPrompt, SessionToken } from "../endpoints";

// ---------- Types ----------
export type Message = { role: "user" | "agent"; content: string };

// ---------- Helpers ----------
function buildAgentMessage(text: string): Message {
    return { role: "agent", content: text };
}

// Map agent -> Gemini prebuilt voice (must match AGENT_VOICES in /api/tts)
const VOICE_MAP: Record<string, string> = {
    DIRECTOR: "Zephyr",
    PILOT: "Puck",
    OBSERVER: "Vega",
};
const DEFAULT_VOICE = "Zephyr"; // fallback to Director voice

function voiceForAuthor(author?: string): string {
    if (!author) return DEFAULT_VOICE;
    const key = String(author).toUpperCase().trim();
    return VOICE_MAP[key] || DEFAULT_VOICE;
}

async function ttsFetch(
    text: string,
    voiceName: string
): Promise<HTMLAudioElement> {
    try {
        const res = await fetch("/api/tts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text, voiceName }),
        });
        if (!res.ok) {
            console.warn(`TTS failed: ${res.status} ${res.statusText}`);
            throw new Error(`TTS ${res.status} ${res.statusText}`);
        }
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        // Cleanup URL after audio finishes
        audio.addEventListener("ended", () => URL.revokeObjectURL(url), {
            once: true,
        });
        return audio;
    } catch (error) {
        console.warn("TTS error:", error);
        throw error;
    }
}

export function Chat({ session }: { session: SessionToken | null }) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [loading, setLoading] = useState(false); // model speaking
    const [canSend, setCanSend] = useState(false);

    // Mic “armed” state (auto-resume after replies)
    const [micArmed, setMicArmed] = useState(false);

    // TTS toggle
    const [ttsEnabled, setTtsEnabled] = useState(true);

    // Is any audio currently playing?
    const [speaking, setSpeaking] = useState(false);

    // Detect speech support **after mount** to avoid hydration drift
    const [support, setSupport] = useState<null | boolean>(null);
    useEffect(() => {
        try {
            setSupport(SpeechRecognition.browserSupportsSpeechRecognition());
        } catch {
            setSupport(false);
        }
    }, []);

    // SpeechRecognition hooks
    const { transcript, listening, resetTranscript } = useSpeechRecognition();

    const inputRef = useRef<HTMLInputElement>(null);
    const decoder = new TextDecoder("utf-8");

    // --- streaming state (to avoid dupes and history wipes) ---
    const streamingTextRef = useRef<string>(""); // accumulates partial text
    const hasStreamedRef = useRef<boolean>(false); // received partials
    const currentAuthorRef = useRef<string | undefined>(undefined); // author for current reply

    // Silence-to-send timer (voice)
    const lastLenRef = useRef<number>(0);
    const silenceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

    // TTS queue (one-at-a-time playback)
    type TTSItem = { text: string; voice: string };
    const ttsQueueRef = useRef<TTSItem[]>([]);
    const ttsPlayingRef = useRef<boolean>(false);

    // Append helper
    const appendMessages = (next: Message | Message[]) => {
        setMessages((prev) => prev.concat(next));
    };

    // Replace the last agent message content (used during streaming)
    const updateLastAgentMessage = (text: string) => {
        setMessages((prev) => {
            if (prev.length === 0) return [buildAgentMessage(text)];
            const copy = prev.slice();
            const last = copy[copy.length - 1];
            if (last.role !== "agent") {
                copy.push(buildAgentMessage(text));
            } else {
                copy[copy.length - 1] = { ...last, content: text };
            }
            return copy;
        });
    };

    // ---- TTS queue worker ----
    const enqueueTTS = (text: string, voice: string) => {
        if (!ttsEnabled) return;
        // Clean up text for TTS
        const cleanText = text.replace(/\[.*?\]/g, "").trim(); // Remove [AGENT] prefixes
        if (!cleanText) return;
        ttsQueueRef.current.push({ text: cleanText, voice });
        runTTSWorker();
    };

    const runTTSWorker = async () => {
        if (ttsPlayingRef.current) return;
        if (!ttsEnabled) {
            // clear queue if disabled
            ttsQueueRef.current = [];
            return;
        }
        const next = ttsQueueRef.current.shift();
        if (!next) return;

        ttsPlayingRef.current = true;
        setSpeaking(true);

        // Pause mic during audio playback
        if (support && listening) SpeechRecognition.stopListening();

        try {
            const audio = await ttsFetch(next.text, next.voice);
            await audio.play();
            await new Promise<void>((resolve) => {
                audio.addEventListener("ended", () => resolve(), {
                    once: true,
                });
                audio.addEventListener(
                    "error",
                    (e) => {
                        console.warn("Audio playback error:", e);
                        resolve();
                    },
                    {
                        once: true,
                    }
                );
                // Add timeout to prevent hanging
                setTimeout(() => resolve(), 10000); // 10 second timeout
            });
        } catch (e) {
            // TTS failed - continue with queue anyway
            console.warn("TTS worker error:", e);
            // If TTS consistently fails, disable it temporarily
            if (
                e instanceof Error &&
                (e.message.includes("503") ||
                    e.message.includes("500") ||
                    e.message.includes("429"))
            ) {
                if (e.message.includes("429")) {
                    console.warn("TTS quota exceeded - disabling temporarily");
                } else {
                    console.warn(
                        "TTS service unavailable - disabling temporarily"
                    );
                }
                setTtsEnabled(false);
                // Clear remaining queue to prevent spam
                ttsQueueRef.current = [];
            }
        } finally {
            ttsPlayingRef.current = false;
            setSpeaking(false);
            runTTSWorker(); // play next
        }
    };

    const handleSendMessage = async (message: string) => {
        if (!session) return;

        const text = message.trim();
        if (!text) return;

        // user msg
        const usr: Message = { role: "user", content: text };
        appendMessages(usr);

        // reset streaming state for new assistant reply
        streamingTextRef.current = "";
        hasStreamedRef.current = false;
        currentAuthorRef.current = undefined;

        setLoading(true);

        // pause mic while model is streaming
        if (support && listening) SpeechRecognition.stopListening();

        try {
            const stream = await sendPrompt(session, text);
            const reader = stream.getReader();

            const pump = async (): Promise<void> => {
                const { done, value } = await reader.read();
                if (done) {
                    setLoading(false);

                    // If we streamed tokens, enqueue TTS for the composed text once
                    if (hasStreamedRef.current && streamingTextRef.current) {
                        const finalText = streamingTextRef.current;
                        const voice = voiceForAuthor(currentAuthorRef.current);
                        enqueueTTS(finalText, voice);
                    }

                    // reset streaming refs for next turn
                    streamingTextRef.current = "";
                    hasStreamedRef.current = false;
                    currentAuthorRef.current = undefined;

                    return;
                }

                const raw = decoder.decode(value);

                // Split by lines and process each one
                const lines = raw.split("\n").filter((line) => line.trim());

                for (const line of lines) {
                    // Remove 'data: ' prefix if present
                    const cleanLine = line.replace(/^data:\s*/g, "").trim();
                    if (!cleanLine || cleanLine === "[DONE]") continue;

                    try {
                        const obj = JSON.parse(cleanLine);
                        handleSSEEvent(obj);
                    } catch (e) {
                        // Skip malformed JSON lines
                        console.warn("Failed to parse SSE line:", cleanLine, e);
                    }
                }

                return pump();
            };

            await pump();
        } catch (e) {
            setLoading(false);
            appendMessages(
                buildAgentMessage("[ERROR] Failed to reach the model.")
            );
            // console.error(e);
        }
    };

    // Handle one SSE JSON event (avoids duplicates)
    const handleSSEEvent = (o: any) => {
        if (!o) return;

        // Extract all text parts in this event
        const parts: string[] = [];
        if (o?.content?.parts && Array.isArray(o.content.parts)) {
            for (const p of o.content.parts) {
                if (p?.text && typeof p.text === "string" && p.text.trim()) {
                    parts.push(p.text);
                }
                // Handle function calls for debugging
                if (p?.functionCall) {
                    const funcName = p.functionCall.name || "unknown";
                    const funcArgs = JSON.stringify(p.functionCall.args || {});
                    parts.push(`CALLING TOOL: ${funcName}(${funcArgs})`);
                }
                if (p?.functionResponse) {
                    const funcName = p.functionResponse.name || "unknown";
                    const funcResp = JSON.stringify(
                        p.functionResponse.response || {}
                    );
                    parts.push(`TOOL RESPONSE: ${funcName}(${funcResp})`);
                }
            }
        }

        if (parts.length === 0) return;
        const joined = parts.join("");

        const author = String(o.author || "agent");
        currentAuthorRef.current = author;

        // Partial token event: update one bubble, accumulate text
        if (o.partial === true) {
            hasStreamedRef.current = true;
            streamingTextRef.current += joined;
            updateLastAgentMessage(
                `[${author.toUpperCase()}] ${streamingTextRef.current}`
            );
            return;
        }

        // Non-partial (final) event:
        // If we already streamed text, ignore appending final (to avoid dupes).
        if (hasStreamedRef.current) {
            // But if there was somehow no accumulated text, use this
            if (!streamingTextRef.current) {
                const msg = `[${author.toUpperCase()}] ${joined}`;
                appendMessages(buildAgentMessage(msg));
                if (ttsEnabled) enqueueTTS(joined, voiceForAuthor(author));
            }
            return;
        }

        // No streaming occurred; append the final once and TTS it.
        const msg = `[${author.toUpperCase()}] ${joined}`;
        appendMessages(buildAgentMessage(msg));
        if (ttsEnabled) enqueueTTS(joined, voiceForAuthor(author));
    };

    // Scroll to bottom on updates
    useEffect(() => {
        const el = document.getElementById("chat-messages");
        if (el) el.scrollTop = el.scrollHeight;
    }, [messages, loading]);

    // Reset on session change
    useEffect(() => {
        setMessages([]);
        inputRef.current && (inputRef.current.value = "");
        setCanSend(false);
        setMicArmed(false);
        streamingTextRef.current = "";
        hasStreamedRef.current = false;
        currentAuthorRef.current = undefined;
        ttsQueueRef.current = [];
        ttsPlayingRef.current = false;
        setSpeaking(false);
        if (support) {
            resetTranscript();
            SpeechRecognition.stopListening();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [session]);

    // Ensure mic paused while model is speaking or TTS is playing
    useEffect(() => {
        if (support && (loading || speaking) && listening) {
            SpeechRecognition.stopListening();
        }
    }, [loading, speaking, listening, support]);

    // Auto-resume mic after model + TTS finish (if armed)
    useEffect(() => {
        if (support && !loading && !speaking && micArmed) {
            const t = setTimeout(() => {
                if (!listening) {
                    resetTranscript();
                    SpeechRecognition.startListening({ continuous: true });
                }
            }, 150);
            return () => clearTimeout(t);
        }
    }, [loading, speaking, micArmed, listening, resetTranscript, support]);

    // Auto-send voice after 1.5s silence (only when actively listening)
    useEffect(() => {
        if (!support || !listening || loading || speaking) return;

        if (silenceTimer.current) {
            clearTimeout(silenceTimer.current);
            silenceTimer.current = null;
        }
        lastLenRef.current = transcript.length;

        silenceTimer.current = setTimeout(() => {
            if (transcript && transcript.length === lastLenRef.current) {
                const text = transcript.trim();
                if (text) handleSendMessage(text);
                resetTranscript();
                SpeechRecognition.stopListening(); // will auto-resume if micArmed when reply+TTS end
            }
        }, 1500);

        return () => {
            if (silenceTimer.current) {
                clearTimeout(silenceTimer.current);
                silenceTimer.current = null;
            }
        };
    }, [transcript, listening, loading, speaking, resetTranscript, support]);

    const toggleMic = () => {
        if (!support || loading || speaking) return;
        if (micArmed) {
            setMicArmed(false);
            SpeechRecognition.stopListening();
            resetTranscript();
        } else {
            setMicArmed(true);
            resetTranscript();
            SpeechRecognition.startListening({ continuous: true });
        }
    };

    return (
        <div className="h-full border-2 border-[#27303e] rounded-md shadow-md bg-[#171717] flex flex-col justify-end gap-2 p-2 text-xs">
            <div className="flex items-center justify-between mb-1">
                <div className="text-gray-300">Chat</div>
                <div className="flex items-center gap-2">
                    <button
                        type="button"
                        onClick={() => setTtsEnabled((v) => !v)}
                        className={`border p-1 px-2 rounded-sm ${
                            ttsEnabled
                                ? "border-indigo-400 text-indigo-300"
                                : "border-gray-500 text-gray-400"
                        }`}
                        title={
                            ttsEnabled
                                ? "Disable agent voices"
                                : "Enable agent voices"
                        }
                    >
                        {ttsEnabled ? (
                            <Volume2 className="w-4 h-4" />
                        ) : (
                            <VolumeX className="w-4 h-4" />
                        )}
                    </button>
                    {support !== null && (
                        <button
                            type="button"
                            onClick={toggleMic}
                            className={`border p-1 px-2 rounded-sm ${
                                loading || speaking
                                    ? "border-gray-700 text-gray-700 cursor-not-allowed"
                                    : support && micArmed
                                    ? "border-green-400 text-green-400"
                                    : support
                                    ? "border-gray-400 text-gray-300 hover:border-white hover:text-white"
                                    : "border-gray-700 text-gray-700 cursor-not-allowed"
                            }`}
                            title={
                                loading || speaking
                                    ? "Disabled while model or TTS is speaking"
                                    : support
                                    ? micArmed
                                        ? "Click to disable mic"
                                        : "Click to enable mic"
                                    : "Speech not supported in this browser"
                            }
                            disabled={loading || speaking || !support}
                        >
                            {support && micArmed ? (
                                <Mic className="w-4 h-4" />
                            ) : (
                                <MicOff className="w-4 h-4" />
                            )}
                        </button>
                    )}
                </div>
            </div>

            <div
                id="chat-messages"
                className="w-full max-h-[320px] bg-[#171717] flex flex-col gap-1 overflow-auto"
            >
                {messages.map((m, i) => (
                    <div
                        key={i}
                        className={`flex ${
                            m.role === "user" ? "justify-end" : "justify-start"
                        }`}
                    >
                        <div
                            className={`max-w-64 text-wrap wrap-break-word overflow-x-hidden px-2 py-1 rounded-sm shadow-sm ${
                                m.role === "user"
                                    ? "bg-green-700 text-white"
                                    : "bg-gray-800 text-white"
                            }`}
                        >
                            {m.content}
                        </div>
                    </div>
                ))}

                {loading && (
                    <div className="w-fit px-2 py-1 rounded-sm shadow-sm bg-gray-800 text-white">
                        <Loader className="animate-spin w-4 h-4 my-auto text-white" />
                    </div>
                )}

                {/* Live transcript bubble while listening */}
                {support &&
                    !loading &&
                    !speaking &&
                    listening &&
                    transcript && (
                        <div className="w-fit px-2 py-1 rounded-sm shadow-sm bg-slate-800/80 text-white border border-slate-600">
                            {transcript}
                        </div>
                    )}
            </div>

            <form
                className="h-fit w-full bg-[#171717] flex flex-row gap-2"
                onSubmit={(e) => {
                    if (!canSend) {
                        e.preventDefault();
                        return;
                    }
                    e.preventDefault();
                    const text = inputRef.current?.value || "";
                    if (text.trim()) handleSendMessage(text);
                    if (inputRef.current) {
                        inputRef.current.value = "";
                        setCanSend(false);
                    }
                }}
            >
                <input
                    onChange={(e) =>
                        setCanSend(
                            session != null && e.target.value.trim() !== ""
                        )
                    }
                    type="text"
                    className="flex-1 px-2 border bg-[#171717] p-1 text-xs rounded-sm border-gray-700 text-white"
                    placeholder="Type a message or use the mic"
                    ref={inputRef}
                    disabled={loading}
                />

                <button
                    type="submit"
                    className={`border bg-[#171717] cursor-pointer w-fit p-1 px-1 rounded-sm text-sm ${
                        canSend && !loading
                            ? "border-white"
                            : "border-gray-700 cursor-not-allowed"
                    }`}
                    disabled={!canSend || loading}
                >
                    <Send
                        className={`w-4 h-4 my-auto ${
                            canSend ? "text-white" : "text-gray-700"
                        }`}
                    />
                </button>
            </form>

            <div className="text-[10px] text-gray-400">
                {support === null
                    ? "Initializing voice…"
                    : support
                    ? micArmed
                        ? speaking
                            ? "Agent is speaking… mic will resume after TTS."
                            : loading
                            ? "Model is speaking… mic will resume after response."
                            : "Mic armed: will auto-resume and auto-send after brief silence."
                        : "Mic off: click mic to start voice capture."
                    : "Voice input not supported in this browser."}
            </div>
        </div>
    );
}
