"use client";

import { useEffect, useMemo, useState } from "react";

type PromptSet = string[];
type ApiState = "idle" | "loading" | "ok" | "error";

const host =
    typeof window !== "undefined" ? window.location.hostname : "localhost";
const ROBOT_BASE = `http://${host}:8889`;
const YOLO_BASE = `http://${host}:8001`;

// -------- fetch helpers --------
async function postJSON(url: string, body: any, opts?: RequestInit) {
    try {
        const res = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
            ...opts,
        });
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        return await res.json();
    } catch (e: any) {
        // Surface network/CORS in a readable way
        throw new Error(e?.message || "Network error (CORS?)");
    }
}

async function postQuery(url: string, params: Record<string, any> = {}) {
    try {
        const qs = new URLSearchParams();
        Object.entries(params).forEach(([k, v]) => {
            if (v !== undefined && v !== null) qs.append(k, String(v));
        });
        const res = await fetch(
            `${url}${qs.toString() ? "?" + qs.toString() : ""}`,
            { method: "POST" }
        );
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        return await res.json();
    } catch (e: any) {
        throw new Error(e?.message || "Network error (CORS?)");
    }
}

export function ManualControls({
    currentPrompts,
}: {
    currentPrompts: string[];
}) {
    // --- robot state ---
    const [speed, setSpeed] = useState(0.5);
    const [duration, setDuration] = useState<number | "">(0.5);
    const [angle, setAngle] = useState<number | "">(45);
    const [robotStatus, setRobotStatus] = useState<ApiState>("idle");

    // --- prompt state ---
    const [promptStatus, setPromptStatus] = useState<ApiState>("idle");
    const [prompts, setPrompts] = useState<PromptSet>([]);
    const [newPrompt, setNewPrompt] = useState("");

    useEffect(() => {
        setPrompts(currentPrompts ?? []);
    }, [currentPrompts]);

    // Also fetch once on mount (in case WS is late)
    useEffect(() => {
        (async () => {
            try {
                const res = await fetch(`${YOLO_BASE}/prompts/`);
                if (res.ok) {
                    const data = await res.json();
                    if (Array.isArray(data?.current_prompts))
                        setPrompts(data.current_prompts);
                }
            } catch {
                /* ignore */
            }
        })();
    }, []);

    // -------- robot actions --------
    async function doForward() {
        try {
            setRobotStatus("loading");
            await postQuery(`${ROBOT_BASE}/forward/`, {
                speed,
                duration: duration === "" ? undefined : duration,
            });
            setRobotStatus("ok");
        } catch (e) {
            console.error(e);
            setRobotStatus("error");
        }
    }

    async function doBackward() {
        try {
            setRobotStatus("loading");
            await postQuery(`${ROBOT_BASE}/backward/`, {
                speed,
                duration: duration === "" ? undefined : duration,
            });
            setRobotStatus("ok");
        } catch (e) {
            console.error(e);
            setRobotStatus("error");
        }
    }

    async function doRotate(delta: number) {
        try {
            setRobotStatus("loading");
            await postQuery(`${ROBOT_BASE}/rotate/`, { angle: delta });
            setRobotStatus("ok");
        } catch (e) {
            console.error(e);
            setRobotStatus("error");
        }
    }

    async function doRotateCustom() {
        if (angle === "" || Number.isNaN(Number(angle))) return;
        return doRotate(Number(angle));
    }

    async function doScan() {
        try {
            setRobotStatus("loading");
            await fetch(`${ROBOT_BASE}/scan/`, { method: "POST" });
            setRobotStatus("ok");
        } catch (e) {
            console.error(e);
            setRobotStatus("error");
        }
    }

    async function doStop() {
        try {
            setRobotStatus("loading");
            await fetch(`${ROBOT_BASE}/stop/`, { method: "POST" });
            setRobotStatus("ok");
        } catch (e) {
            console.error(e);
            setRobotStatus("error");
        }
    }

    // -------- prompt actions --------
    async function setPromptList(next: PromptSet) {
        try {
            setPromptStatus("loading");
            const res = await postJSON(`${YOLO_BASE}/prompts/`, next);
            if (res?.success) setPrompts(next);
            setPromptStatus(res?.success ? "ok" : "error");
        } catch (e) {
            console.error(e);
            setPromptStatus("error");
        }
    }

    async function appendPrompts(newOnes: PromptSet) {
        try {
            setPromptStatus("loading");
            // Try append endpoint
            const res = await postJSON(`${YOLO_BASE}/append-prompts/`, newOnes);
            if (res?.success && Array.isArray(res?.current_prompts)) {
                setPrompts(res.current_prompts);
                setPromptStatus("ok");
                return;
            }
            // Fallback: merge locally and set
            const merged = Array.from(new Set([...prompts, ...newOnes]));
            await setPromptList(merged);
        } catch (e) {
            console.warn("append failed, fallback to set", e);
            const merged = Array.from(new Set([...prompts, ...newOnes]));
            await setPromptList(merged);
        }
    }

    function removePrompt(idx: number) {
        const next = prompts.filter((_, i) => i !== idx);
        setPromptList(next);
    }

    function addPromptFromInput() {
        const candidate = newPrompt.trim();
        if (!candidate) return;
        appendPrompts([candidate]);
        setNewPrompt("");
    }

    const quickSets: PromptSet[] = useMemo(
        () => [
            ["person", "bottle"],
            ["person", "car", "chair"],
            ["dog", "cat"],
            ["cup", "bottle", "laptop", "phone"],
        ],
        []
    );

    const badge = (st: ApiState) =>
        ({
            idle: "bg-gray-600",
            loading: "bg-yellow-600 animate-pulse",
            ok: "bg-green-600",
            error: "bg-red-600",
        }[st]);

    return (
        <div className="h-full flex flex-col border-2 border-[#27303e] rounded-md shadow-md bg-[#171717] p-2 text-xs text-gray-100">
            {/* scrollable content */}
            <div className="flex-1 flex flex-col gap-2 overflow-y-auto pr-1">
                {/* Robot Controls */}
                <div className="border-2 border-[#27303e] rounded-md bg-[#1f2630] p-2">
                    <div className="flex items-center justify-between mb-2">
                        <div className="font-bold text-green-300">
                            Robot Controls
                        </div>
                        <div
                            className={`w-2 h-2 rounded-full ${badge(
                                robotStatus
                            )}`}
                        />
                    </div>

                    {/* speed & duration */}
                    <div className="grid grid-cols-2 gap-2">
                        <div className="flex flex-col">
                            <label className="text-gray-400 mb-1">Speed</label>
                            <div className="flex items-center gap-2">
                                <input
                                    type="range"
                                    min={0}
                                    max={1}
                                    step={0.05}
                                    value={speed}
                                    onChange={(e) =>
                                        setSpeed(parseFloat(e.target.value))
                                    }
                                    className="w-full accent-green-500"
                                />
                                <span className="w-10 text-right">
                                    {speed.toFixed(2)}
                                </span>
                            </div>
                            <div className="text-[10px] text-gray-400 mt-1">
                                0..1 (motor scale)
                            </div>
                        </div>

                        <div className="flex flex-col">
                            <label className="text-gray-400 mb-1">
                                Duration (s)
                            </label>
                            <div className="flex items-center gap-2">
                                <input
                                    type="number"
                                    step="0.1"
                                    min="0"
                                    placeholder="blank = continuous"
                                    value={duration}
                                    onChange={(e) =>
                                        setDuration(
                                            e.target.value === ""
                                                ? ""
                                                : Number(e.target.value)
                                        )
                                    }
                                    className="w-full bg-[#111418] border border-[#2b3442] rounded px-2 py-1"
                                />
                                <button
                                    className="px-2 py-1 bg-gray-700 hover:bg-gray-800 rounded"
                                    onClick={() => setDuration("")}
                                >
                                    ∞
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* D-Pad */}
                    <div className="grid grid-cols-3 gap-2 mt-3">
                        <div />
                        <button
                            className="py-2 bg-green-700 hover:bg-green-800 rounded shadow"
                            onClick={doForward}
                        >
                            ↑ Forward
                        </button>
                        <div />

                        <button
                            className="py-2 bg-blue-700 hover:bg-blue-800 rounded shadow"
                            onClick={() => doRotate(-15)}
                        >
                            ↺ 15°
                        </button>
                        <button
                            className="py-2 bg-red-700 hover:bg-red-800 rounded shadow sticky top-2"
                            onClick={doStop}
                            title="Emergency stop"
                        >
                            ■ STOP
                        </button>
                        <button
                            className="py-2 bg-blue-700 hover:bg-blue-800 rounded shadow"
                            onClick={() => doRotate(15)}
                        >
                            15° ↻
                        </button>

                        <div />
                        <button
                            className="py-2 bg-green-700 hover:bg-green-800 rounded shadow"
                            onClick={doBackward}
                        >
                            ↓ Backward
                        </button>
                        <div />
                    </div>

                    {/* rotate presets + custom */}
                    <div className="mt-2 flex flex-wrap gap-2">
                        {[5, 15, 45, 90, 180].map((a) => (
                            <button
                                key={`l${a}`}
                                className="px-2 py-1 bg-blue-700 hover:bg-blue-800 rounded"
                                onClick={() => doRotate(-a)}
                                title={`Rotate left ${a}°`}
                            >
                                ↺ {a}°
                            </button>
                        ))}
                        {[5, 15, 45, 90, 180].map((a) => (
                            <button
                                key={`r${a}`}
                                className="px-2 py-1 bg-blue-700 hover:bg-blue-800 rounded"
                                onClick={() => doRotate(a)}
                                title={`Rotate right ${a}°`}
                            >
                                {a}° ↻
                            </button>
                        ))}

                        <div className="ml-auto flex items-center gap-2">
                            <input
                                type="number"
                                step="1"
                                className="w-20 bg-[#111418] border border-[#2b3442] rounded px-2 py-1"
                                value={angle}
                                onChange={(e) =>
                                    setAngle(
                                        e.target.value === ""
                                            ? ""
                                            : Number(e.target.value)
                                    )
                                }
                                placeholder="deg"
                            />
                            <button
                                className="px-2 py-1 bg-blue-700 hover:bg-blue-800 rounded"
                                onClick={doRotateCustom}
                            >
                                Rotate
                            </button>
                            <button
                                className="px-2 py-1 bg-purple-700 hover:bg-purple-800 rounded"
                                onClick={doScan}
                            >
                                Scan 360°
                            </button>
                        </div>
                    </div>
                </div>

                {/* Prompt Controls */}
                <div className="border-2 border-[#27303e] rounded-md bg-[#1f2630] p-2">
                    <div className="flex items-center justify-between mb-2">
                        <div className="font-bold text-green-300">
                            YOLO Prompts
                        </div>
                        <div
                            className={`w-2 h-2 rounded-full ${badge(
                                promptStatus
                            )}`}
                        />
                    </div>

                    {/* Chips */}
                    <div className="flex flex-wrap gap-2">
                        {prompts.length === 0 && (
                            <span className="text-gray-400 text-[11px]">
                                No prompts set
                            </span>
                        )}
                        {prompts.map((p, i) => (
                            <span
                                key={`${p}-${i}`}
                                className="inline-flex items-center gap-1 bg-[#2a3442] border border-[#334155] rounded px-2 py-1"
                            >
                                <span>{p}</span>
                                <button
                                    className="text-red-300 hover:text-red-500"
                                    onClick={() => removePrompt(i)}
                                    title="Remove prompt"
                                >
                                    ✕
                                </button>
                            </span>
                        ))}
                    </div>

                    {/* Add */}
                    <div className="mt-2 flex gap-2">
                        <input
                            type="text"
                            className="flex-1 bg-[#111418] border border-[#2b3442] rounded px-2 py-1"
                            placeholder="add a prompt (e.g., red bottle)"
                            value={newPrompt}
                            onChange={(e) => setNewPrompt(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === "Enter") addPromptFromInput();
                            }}
                        />
                        <button
                            className="px-2 py-1 bg-green-700 hover:bg-green-800 rounded"
                            onClick={addPromptFromInput}
                        >
                            Add
                        </button>
                        <button
                            className="px-2 py-1 bg-amber-700 hover:bg-amber-800 rounded"
                            onClick={() => setPromptList([])}
                            title="Clear all prompts"
                        >
                            Clear
                        </button>
                    </div>

                    {/* Quick sets */}
                    <div className="mt-2 flex flex-wrap gap-2">
                        {quickSets.map((qs, idx) => (
                            <button
                                key={idx}
                                className="px-2 py-1 bg-gray-700 hover:bg-gray-800 rounded"
                                onClick={() => setPromptList(qs)}
                                title={`Set prompts: ${qs.join(", ")}`}
                            >
                                {qs.join(" • ")}
                            </button>
                        ))}
                        <button
                            className="ml-auto px-2 py-1 bg-sky-700 hover:bg-sky-800 rounded"
                            onClick={async () => {
                                try {
                                    setPromptStatus("loading");
                                    const res = await fetch(
                                        `${YOLO_BASE}/prompts/`
                                    );
                                    if (res.ok) {
                                        const data = await res.json();
                                        if (
                                            Array.isArray(data?.current_prompts)
                                        ) {
                                            setPrompts(data.current_prompts);
                                        }
                                    }
                                    setPromptStatus("ok");
                                } catch {
                                    setPromptStatus("error");
                                }
                            }}
                            title="Refresh from backend"
                        >
                            Refresh
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
