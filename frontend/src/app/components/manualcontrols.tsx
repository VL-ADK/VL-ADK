"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type PromptSet = string[];
type ApiState = "idle" | "loading" | "ok" | "error";

const host =
    typeof window !== "undefined" ? window.location.hostname : "localhost";
const ROBOT_BASE = `http://${host}:8889`;
const YOLO_BASE = `http://${host}:8001`;

// -------- fetch helpers --------
async function postJSON(url: string, body: any, opts?: RequestInit) {
    const res = await fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        mode: "cors",
        body: JSON.stringify(body),
        ...opts,
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return await res.json();
}

async function postQuery(url: string, params: Record<string, any> = {}) {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null) qs.append(k, String(v));
    });
    const res = await fetch(
        `${url}${qs.toString() ? "?" + qs.toString() : ""}`,
        {
            method: "POST",
            mode: "cors",
        }
    );
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return await res.json();
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

    // --- keyboard control state ---
    const [keysPressed, setKeysPressed] = useState<Set<string>>(new Set());
    const [isApiCallInProgress, setIsApiCallInProgress] = useState(false);
    const keyboardIntervalRef = useRef<NodeJS.Timeout | null>(null);

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

    // -------- keyboard control logic --------
    const processKeyboardMovement = useCallback(async () => {
        if (keysPressed.size === 0) return;

        // Skip if API call is in progress, but don't block the whole system
        if (isApiCallInProgress) {
            console.log("API call in progress, skipping...");
            return;
        }

        try {
            // Priority: Stop > Movement > Rotation
            if (keysPressed.has(" ") || keysPressed.has("Escape")) {
                console.log("Emergency stop triggered");
                setIsApiCallInProgress(true);
                setRobotStatus("loading");
                await fetch(`${ROBOT_BASE}/stop/`, {
                    method: "POST",
                    mode: "cors",
                });
                setRobotStatus("ok");
                return;
            }

            // Movement (forward/backward takes priority over rotation)
            if (
                keysPressed.has("ArrowUp") ||
                keysPressed.has("w") ||
                keysPressed.has("W")
            ) {
                console.log("Moving forward");
                await doKeyboardForward();
            } else if (
                keysPressed.has("ArrowDown") ||
                keysPressed.has("s") ||
                keysPressed.has("S")
            ) {
                console.log("Moving backward");
                await doKeyboardBackward();
            } else if (
                keysPressed.has("ArrowLeft") ||
                keysPressed.has("a") ||
                keysPressed.has("A")
            ) {
                console.log("Rotating left");
                await doKeyboardRotate(-25); // 25 degrees left for smoother rotation
            } else if (
                keysPressed.has("ArrowRight") ||
                keysPressed.has("d") ||
                keysPressed.has("D")
            ) {
                console.log("Rotating right");
                await doKeyboardRotate(25); // 25 degrees right for smoother rotation
            }
        } catch (error) {
            console.error("Keyboard movement error:", error);
            setRobotStatus("error");
        } finally {
            setIsApiCallInProgress(false);
        }
    }, [keysPressed, isApiCallInProgress, speed]);

    // Keyboard event handlers
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            // Only handle if we're not focused on an input
            if (e.target instanceof HTMLInputElement) return;

            const validKeys = [
                "ArrowUp",
                "ArrowDown",
                "ArrowLeft",
                "ArrowRight",
                "w",
                "W",
                "a",
                "A",
                "s",
                "S",
                "d",
                "D",
                " ",
                "Escape",
            ];
            if (!validKeys.includes(e.key)) return;

            e.preventDefault();
            setKeysPressed((prev) => new Set([...prev, e.key]));
        };

        const handleKeyUp = (e: KeyboardEvent) => {
            if (e.target instanceof HTMLInputElement) return;

            const validKeys = [
                "ArrowUp",
                "ArrowDown",
                "ArrowLeft",
                "ArrowRight",
                "w",
                "W",
                "a",
                "A",
                "s",
                "S",
                "d",
                "D",
                " ",
                "Escape",
            ];
            if (!validKeys.includes(e.key)) return;

            e.preventDefault();
            setKeysPressed((prev) => {
                const next = new Set(prev);
                next.delete(e.key);
                return next;
            });
        };

        window.addEventListener("keydown", handleKeyDown);
        window.addEventListener("keyup", handleKeyUp);

        return () => {
            window.removeEventListener("keydown", handleKeyDown);
            window.removeEventListener("keyup", handleKeyUp);
        };
    }, []);

    // Process keyboard movement continuously
    useEffect(() => {
        if (keysPressed.size > 0) {
            // Start immediately on key press
            processKeyboardMovement();
            // Then continue with intervals - 600ms to work with 0.8s duration commands
            keyboardIntervalRef.current = setInterval(
                processKeyboardMovement,
                600
            ); // ~1.7Hz update rate - allows commands to overlap slightly for smooth movement
        } else {
            // Clear the interval when no keys are pressed
            if (keyboardIntervalRef.current) {
                clearInterval(keyboardIntervalRef.current);
                keyboardIntervalRef.current = null;
            }
        }

        // Cleanup on unmount
        return () => {
            if (keyboardIntervalRef.current) {
                clearInterval(keyboardIntervalRef.current);
                keyboardIntervalRef.current = null;
            }
        };
    }, [keysPressed, processKeyboardMovement]);

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

    // Keyboard-specific continuous movement (with duration for continuous hold)
    async function doKeyboardForward() {
        if (isApiCallInProgress) return;
        try {
            setIsApiCallInProgress(true);
            setRobotStatus("loading");
            await postQuery(`${ROBOT_BASE}/forward/`, {
                speed,
                duration: 0.8, // Longer duration for smoother movement
            });
            setRobotStatus("ok");
        } catch (e) {
            console.error(e);
            setRobotStatus("error");
        } finally {
            setIsApiCallInProgress(false);
        }
    }

    async function doKeyboardBackward() {
        if (isApiCallInProgress) return;
        try {
            setIsApiCallInProgress(true);
            setRobotStatus("loading");
            await postQuery(`${ROBOT_BASE}/backward/`, {
                speed,
                duration: 0.8, // Longer duration for smoother movement
            });
            setRobotStatus("ok");
        } catch (e) {
            console.error(e);
            setRobotStatus("error");
        } finally {
            setIsApiCallInProgress(false);
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

    async function doKeyboardRotate(delta: number) {
        if (isApiCallInProgress) return;
        try {
            setIsApiCallInProgress(true);
            setRobotStatus("loading");
            await postQuery(`${ROBOT_BASE}/rotate/`, {
                angle: delta,
                // Rotation doesn't need duration - it's an instant command
            });
            setRobotStatus("ok");
        } catch (e) {
            console.error(e);
            setRobotStatus("error");
        } finally {
            setIsApiCallInProgress(false);
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

    const badge = (st: ApiState) =>
        ({
            idle: "bg-gray-600",
            loading: "bg-yellow-600 animate-pulse",
            ok: "bg-green-600",
            error: "bg-red-600",
        }[st]);

    return (
        <div className="h-full flex flex-col border-2 border-[#27303e] rounded-md shadow-md bg-[#171717] p-2 text-xs text-gray-100 min-h-0">
            {/* scrollable content */}
            <div className="flex-1 flex flex-col gap-2 overflow-y-auto pr-1 min-h-0">
                {/* Robot Controls - Takes more space */}
                <div className="flex-1 border-2 border-[#27303e] rounded-md bg-[#1f2630] p-2 flex flex-col min-h-0">
                    <div className="flex items-center justify-between mb-2">
                        <div className="font-bold text-green-300">
                            Robot Controls
                            {keysPressed.size > 0 && (
                                <span className="ml-2 text-xs text-yellow-400 animate-pulse">
                                    KEYBOARD ACTIVE
                                </span>
                            )}
                        </div>
                        <div className="flex items-center gap-2">
                            {isApiCallInProgress && (
                                <div className="text-xs text-yellow-400 animate-pulse">
                                    API
                                </div>
                            )}
                            <div
                                className={`w-2 h-2 rounded-full ${badge(
                                    robotStatus
                                )}`}
                            />
                        </div>
                    </div>

                    {/* Keyboard controls help */}
                    <div className="mb-3 p-2 bg-gray-800 rounded text-[10px] text-gray-300">
                        <div className="font-semibold mb-1">
                            Keyboard Controls:
                        </div>
                        <div className="grid grid-cols-2 gap-1 text-[9px]">
                            <div>↑/W: Forward</div>
                            <div>↓/S: Backward</div>
                            <div>←/A: Turn Left</div>
                            <div>→/D: Turn Right</div>
                            <div>SPACE: Emergency Stop</div>
                            <div>ESC: Emergency Stop</div>
                        </div>
                        {keysPressed.size > 0 && (
                            <div className="mt-2 text-yellow-400">
                                Active: {Array.from(keysPressed).join(", ")}
                            </div>
                        )}
                    </div>

                    {/* speed & duration */}
                    <div className="grid grid-cols-2 gap-4 mb-4">
                        <div className="flex flex-col">
                            <label className="text-gray-400 mb-2 text-sm">
                                Speed
                            </label>
                            <div className="flex items-center gap-3">
                                <input
                                    type="range"
                                    min={0}
                                    max={1}
                                    step={0.05}
                                    value={speed}
                                    onChange={(e) =>
                                        setSpeed(parseFloat(e.target.value))
                                    }
                                    className="w-full accent-green-500 h-3"
                                />
                                <span className="w-12 text-right font-mono text-sm">
                                    {speed.toFixed(2)}
                                </span>
                            </div>
                            <div className="text-[10px] text-gray-400 mt-2">
                                0..1 (motor scale)
                            </div>
                        </div>

                        <div className="flex flex-col">
                            <label className="text-gray-400 mb-2 text-sm">
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
                                    className="w-full bg-[#111418] border border-[#2b3442] rounded px-3 py-2 text-sm"
                                />
                                <button
                                    className="px-3 py-2 bg-gray-700 hover:bg-gray-800 rounded text-sm"
                                    onClick={() => setDuration("")}
                                >
                                    ∞
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* D-Pad - Takes more space */}
                    <div className="flex-1 flex flex-col justify-center">
                        <div className="grid grid-cols-3 gap-3">
                            <div />
                            <button
                                className="py-4 bg-green-700 hover:bg-green-800 rounded shadow text-sm font-semibold"
                                onClick={doForward}
                            >
                                ↑ Forward
                            </button>
                            <div />

                            <button
                                className="py-4 bg-blue-700 hover:bg-blue-800 rounded shadow text-sm font-semibold"
                                onClick={() => doRotate(-15)}
                            >
                                ↺ 15°
                            </button>
                            <button
                                className="py-4 bg-red-700 hover:bg-red-800 rounded shadow sticky top-2 text-sm font-bold"
                                onClick={doStop}
                                title="Emergency stop"
                            >
                                ■ STOP
                            </button>
                            <button
                                className="py-4 bg-blue-700 hover:bg-blue-800 rounded shadow text-sm font-semibold"
                                onClick={() => doRotate(15)}
                            >
                                15° ↻
                            </button>

                            <div />
                            <button
                                className="py-4 bg-green-700 hover:bg-green-800 rounded shadow text-sm font-semibold"
                                onClick={doBackward}
                            >
                                ↓ Backward
                            </button>
                            <div />
                        </div>
                    </div>

                    {/* rotate presets + custom */}
                    <div className="mt-4 flex flex-wrap gap-2">
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
                            className={`w-2 h-2 rounded-full ${
                                {
                                    idle: "bg-gray-600",
                                    loading: "bg-yellow-600 animate-pulse",
                                    ok: "bg-green-600",
                                    error: "bg-red-600",
                                }[promptStatus]
                            }`}
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
                                        )
                                            setPrompts(data.current_prompts);
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
