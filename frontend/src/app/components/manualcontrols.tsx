"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ControlMessage, controlWsURL } from "../websocket";
import { EraserIcon, RefreshCwIcon, SendIcon } from "lucide-react";

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
    const [angularVelocity, setAngularVelocity] = useState(0.5);
    const [duration, setDuration] = useState<number | "">(0.5);
    const [degrees, setDegrees] = useState<number | "">(45);
    const [robotStatus, setRobotStatus] = useState<ApiState>("idle");

    // --- keyboard control state ---
    const [keysPressed, setKeysPressed] = useState<Set<string>>(new Set());

    // --- WebSocket control ---
    const controlWsRef = useRef<WebSocket | null>(null);
    const [wsConnected, setWsConnected] = useState(false);

    // --- prompt state ---
    const [promptStatus, setPromptStatus] = useState<ApiState>("idle");
    const [prompts, setPrompts] = useState<PromptSet>([]);
    const [newPrompt, setNewPrompt] = useState("");

    const refreshYOLO = async () => {
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
    }

    useEffect(() => {
        setPrompts(currentPrompts ?? []);
    }, [currentPrompts]);

    // Initialize WebSocket control connection
    useEffect(() => {
        const connectControlWS = () => {
            try {
                controlWsRef.current = new WebSocket(controlWsURL);

                controlWsRef.current.onopen = () => {
                    console.log("Connected to robot control WebSocket");
                    setWsConnected(true);
                };

                controlWsRef.current.onclose = () => {
                    console.log(
                        "Robot control WebSocket disconnected, retrying in 3 seconds..."
                    );
                    setWsConnected(false);
                    setTimeout(connectControlWS, 3000);
                };

                controlWsRef.current.onerror = (error) => {
                    console.error("Control WebSocket error:", error);
                    setWsConnected(false);
                };
            } catch (error) {
                console.error("Failed to create control WebSocket:", error);
                setTimeout(connectControlWS, 3000);
            }
        };

        connectControlWS();

        refreshYOLO();

        return () => {
            if (controlWsRef.current) {
                controlWsRef.current.close();
            }
        };
    }, []);

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

    // -------- WebSocket control helper --------
    const sendControlMessage = useCallback(
        (message: ControlMessage) => {
            if (controlWsRef.current && wsConnected) {
                try {
                    controlWsRef.current.send(JSON.stringify(message));
                    console.log("Sent control message:", message);
                    return true;
                } catch (error) {
                    console.error("Failed to send control message:", error);
                    return false;
                }
            }
            return false;
        },
        [wsConnected]
    );

    // -------- keyboard control logic --------
    const processKeyboardMovement = useCallback(() => {
        if (keysPressed.size === 0) return;

        if (!wsConnected) {
            console.log("WebSocket not connected, skipping control");
            return;
        }

        try {
            setRobotStatus("loading");

            // Priority: Stop > Movement > Rotation
            if (keysPressed.has(" ") || keysPressed.has("Escape")) {
                console.log("Emergency stop triggered");
                if (sendControlMessage({ action: "stop" })) {
                    setRobotStatus("ok");
                } else {
                    setRobotStatus("error");
                }
                return;
            }

            // Movement (forward/backward takes priority over rotation)
            if (
                keysPressed.has("ArrowUp") ||
                keysPressed.has("w") ||
                keysPressed.has("W")
            ) {
                console.log("Moving forward");
                if (
                    sendControlMessage({
                        action: "forward",
                        linear_velocity: speed,
                    })
                ) {
                    setRobotStatus("ok");
                } else {
                    setRobotStatus("error");
                }
            } else if (
                keysPressed.has("ArrowDown") ||
                keysPressed.has("s") ||
                keysPressed.has("S")
            ) {
                console.log("Moving backward");
                if (
                    sendControlMessage({
                        action: "backward",
                        linear_velocity: speed,
                    })
                ) {
                    setRobotStatus("ok");
                } else {
                    setRobotStatus("error");
                }
            } else if (
                keysPressed.has("ArrowLeft") ||
                keysPressed.has("a") ||
                keysPressed.has("A")
            ) {
                console.log("Rotating left");
                if (
                    sendControlMessage({
                        action: "left",
                        angular_velocity: angularVelocity,
                    })
                ) {
                    setRobotStatus("ok");
                } else {
                    setRobotStatus("error");
                }
            } else if (
                keysPressed.has("ArrowRight") ||
                keysPressed.has("d") ||
                keysPressed.has("D")
            ) {
                console.log("Rotating right");
                if (
                    sendControlMessage({
                        action: "right",
                        angular_velocity: angularVelocity,
                    })
                ) {
                    setRobotStatus("ok");
                } else {
                    setRobotStatus("error");
                }
            }
        } catch (error) {
            console.error("Keyboard movement error:", error);
            setRobotStatus("error");
        }
    }, [keysPressed, wsConnected, speed, angularVelocity, sendControlMessage]);

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

    // Process keyboard movement - immediate start/stop, no intervals
    useEffect(() => {
        if (keysPressed.size > 0 && wsConnected) {
            // Start movement immediately when key is pressed
            processKeyboardMovement();
        } else if (keysPressed.size === 0 && wsConnected) {
            // Stop immediately when all keys are released
            sendControlMessage({ action: "stop" });
        }
    }, [keysPressed, wsConnected, processKeyboardMovement, sendControlMessage]);

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

    // Note: Keyboard movement now uses WebSocket via processKeyboardMovement function

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

    // Note: Keyboard rotation now uses WebSocket via processKeyboardMovement function

    async function doRotateCustom(direction = 1) {
        const degreesToRotate =
            degrees === "" || Number.isNaN(Number(degrees))
                ? 45
                : Number(degrees);
        return doRotate(direction * degreesToRotate);
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
        <div className="h-full flex flex-col min-h-0">
            {/* scrollable content */}
            <div className="grid grid-rows-3 gap-1 overflow-y-auto h-full">
                {/* Robot Controls - Takes more space */}
                <div className="row-span-2 flex-1 border-2 border-[#27303e] shadow-md rounded-md bg-[#171717] p-2 flex flex-col min-h-0">
                    <div className="flex items-center justify-between mb-2">
                        KEYBOARD CONTROLS
                        <div className="flex items-center gap-2">
                            <div
                                className={`w-2 h-2 rounded-full ${badge(
                                    robotStatus
                                )}`}
                            />
                            <div className="text-xs text-gray-300">
                                {robotStatus.toUpperCase()}
                            </div>
                        </div>
                    </div>

                    {/* Keyboard controls help */}
                    <div className="mb-3 rounded text-[10px] text-gray-300">
                        <div className="grid grid-cols-2 gap-1 text-xs">
                            <div className={`text-gray-400 border-b-2 border-gray-900 ${keysPressed.has("ArrowUp") || keysPressed.has("w") ? "bg-gray-900" : "bg-gray-800"} rounded-md p-1`}>[↑/W] Forward</div>
                            <div className={`text-gray-400 border-b-2 border-gray-900 ${keysPressed.has("ArrowDown") || keysPressed.has("s") ? "bg-gray-900" : "bg-gray-800"} rounded-md p-1`}>[↓/S] Backward</div>
                            <div className={`text-gray-400 border-b-2 border-gray-900 ${keysPressed.has("ArrowLeft") || keysPressed.has("a") ? "bg-gray-900" : "bg-gray-800"} rounded-md p-1`}>[←/A] Turn Left</div>
                            <div className={`text-gray-400 border-b-2 border-gray-900 ${keysPressed.has("ArrowRight") || keysPressed.has("d") ? "bg-gray-900" : "bg-gray-800"} rounded-md p-1`}>[→/D] Turn Right</div>
                            <div className={`text-gray-400 border-b-2 border-gray-900 ${keysPressed.has(" ") ? "bg-gray-900" : "bg-gray-800"}  rounded-md p-1`}>[SPACE] Emergency Stop</div>
                            <div className={`text-gray-400 border-b-2 border-gray-900 ${keysPressed.has("Escape") ? "bg-gray-900" : "bg-gray-800"} rounded-md p-1`}>[ESC] Emergency Stop</div>
                        </div>
                    </div>

                    {/* speed & duration */}
                    <div className="flex flex-row w-full gap-4 mb-4">
                        <div className="flex flex-col">
                            <label className="text-gray-400 mb-2 text-sm">
                                LINEAR SPEED <span className="text-xs text-gray-400">(FORWARD/BACKWARD)</span>
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
                        </div>
                    </div>

                    {/* angular speed & degrees */}
                    <div className="flex flex-row w-full gap-4 mb-4">
                        <div className="flex flex-col">
                            <label className="text-gray-400 mb-2 text-sm">
                                ANGULAR SPEED <span className="text-xs text-gray-400">(TURNING)</span>
                            </label>
                            <div className="flex items-center gap-3">
                                <input
                                    type="range"
                                    min={0}
                                    max={1}
                                    step={0.05}
                                    value={angularVelocity}
                                    onChange={(e) =>
                                        setAngularVelocity(
                                            parseFloat(e.target.value)
                                        )
                                    }
                                    className="w-full accent-blue-500 h-3"
                                />
                                <span className="w-12 text-right font-mono text-sm">
                                    {angularVelocity.toFixed(2)}
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* D-Pad - Takes more space */}
                    <div className="flex-1 flex flex-col justify-center hidden">
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
                                onClick={() => doRotateCustom(-1)}
                                title={`Rotate left ${degrees || 45}°`}
                            >
                                ↺ {degrees || 45}°
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
                                onClick={() => doRotateCustom(1)}
                                title={`Rotate right ${degrees || 45}°`}
                            >
                                {degrees || 45}° ↻
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

                    {/* custom rotation + scan */}
                    <div className="mt-4 flex items-center justify-between hidden">
                        <div className="flex items-center gap-2">
                            <button
                                className="px-3 py-2 bg-blue-700 hover:bg-blue-800 rounded text-sm"
                                onClick={() => doRotateCustom(-1)}
                                title={`Rotate left ${degrees || 45}°`}
                            >
                                ↺ Rotate Left
                            </button>
                            <button
                                className="px-3 py-2 bg-blue-700 hover:bg-blue-800 rounded text-sm"
                                onClick={() => doRotateCustom(1)}
                                title={`Rotate right ${degrees || 45}°`}
                            >
                                Rotate Right ↻
                            </button>
                        </div>
                        <button
                            className="px-3 py-2 bg-purple-700 hover:bg-purple-800 rounded text-sm"
                            onClick={doScan}
                        >
                            Scan 360°
                        </button>
                    </div>
                </div>

                {/* Prompt Controls */}
                <div className="border-2 border-[#27303e] rounded-md shadow-md bg-[#171717] p-2 flex flex-col justify-between">
                    <div className="flex flex-col">
                        <div className="flex items-center justify-between mb-2">
                            <div className="text-xs">
                                YOLO PROMPTS
                            </div>
                            <div className="flex flex-row gap-2">
                                <div
                                    className={`w-2 h-2 my-auto rounded-full ${
                                        {
                                            idle: "bg-gray-600",
                                            loading: "bg-yellow-600 animate-pulse",
                                            ok: "bg-green-600",
                                            error: "bg-red-600",
                                        }[promptStatus]
                                    }`}
                                />
                                <div className="text-xs my-auto">{promptStatus.toUpperCase()}</div>
                            </div>
                            
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
                                    className="inline-flex text-xs items-center gap-1 bg-gray-700 border-b-2 border-gray-800 rounded-md px-2 py-1"
                                >
                                    <span>{p}</span>
                                    <button
                                        className="text-red-600 hover:text-red-700 my-auto cursor-pointer"
                                        onClick={() => removePrompt(i)}
                                        title="Remove prompt"
                                    >
                                        ✕
                                    </button>
                                </span>
                            ))}
                        </div>

                    </div>

                    {/* Add */}
                    <div className="mt-2 flex gap-2 text-xs">
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
                            className="p-1 cursor-pointer border border-[#ededed] rounded"
                            onClick={addPromptFromInput}
                        >
                            <SendIcon className="w-4 h-4" />
                        </button>
                        <button
                            className="p-1 cursor-pointer border border-[#ededed] rounded"
                            onClick={() => setPromptList([])}
                            title="Clear all prompts"
                        >
                            <EraserIcon className="w-4 h-4" />
                        </button>
                        <button
                            className="ml-auto p-1 cursor-pointer border border-[#ededed] rounded"
                            onClick={refreshYOLO}
                            title="Refresh from backend"
                        >
                            <RefreshCwIcon className="w-4 h-4" />
                        </button>
                    </div>
                    
                </div>
            </div>
        </div>
    );
}
