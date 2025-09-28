"use client";
import { useEffect, useRef, useState } from "react";
import { AgentGraph } from "./components/agentgraph";
import { Chat } from "./components/chat";
import { ManualControls } from "./components/manualcontrols";
import Motor from "./components/motor";
import { Radar } from "./components/radar";
import { VideoStream } from "./components/videostream";
import { eStop, SessionToken, startSession } from "./endpoints";
import { annotationWsURL, ControlSchema, MotorData } from "./websocket";

export default function Home() {
    const annotationWs = useRef<WebSocket | null>(null);
    const [image, setImage] = useState<string | undefined>("");
    const [motorData, setMotorData] = useState<MotorData | null>(null);
    const [control, setControl] = useState<ControlSchema | null>(null);
    const [session, setSession] = useState<SessionToken | null>(null);
    const [currentPrompts, setCurrentPrompts] = useState<string[]>([]);

    const AGENT_GRAPH = 0;
    const RADAR = 1;
    const MOTOR_DATA = 2;

    const [tab, setTab] = useState<number>(AGENT_GRAPH);

    function connectAnnotationWS() {
        try {
            annotationWs.current = new WebSocket(annotationWsURL);

            annotationWs.current.onopen = () => {
                console.log("Connected to annotation stream (YOLO:8002)");
            };

            annotationWs.current.onmessage = (event) => {
                const body: any = JSON.parse(event.data);

                // YOLO sends annotated images: { "image": "base64...", "annotations": [...], "motor_data": {...}, "current_prompts": [...] }
                if (body.image) {
                    setImage(body.image); // Use the annotated image with bboxes already drawn
                }
                // Extract motor data if available
                if (body.motor_data) {
                    setMotorData({
                        left_motor: body.motor_data.left_motor || 0,
                        right_motor: body.motor_data.right_motor || 0,
                    });
                }
                // Extract current prompts if available
                if (body.current_prompts) {
                    setCurrentPrompts(body.current_prompts);
                }
            };

            annotationWs.current.onerror = (event) => {
                console.log("Annotation WebSocket error:", event);
            };

            annotationWs.current.onclose = () => {
                console.log(
                    "YOLO WebSocket disconnected, retrying in 5 seconds..."
                );
                setImage("");
                setTimeout(() => {
                    connectAnnotationWS();
                }, 5000);
            };
        } catch (error) {
            console.log("Annotation WebSocket error:", error);
        }
    }

    useEffect(() => {
        connectAnnotationWS(); // Only connect to YOLO annotated stream
        startSession().then((session) => {
            setSession(session);
            console.log(session);
        });
    }, []);

    return (
        <div className="h-dvh w-dvw flex flex-col font-mono p-2 gap-2">
            <div className="text-2xl font-bold w-full p-1 px-2 bg-gradient-to-b from-[#364153] to-[#27303e] border-[#27303e] shadow-md flex flex-row justify-between border-2 rounded-md">
                <div className="flex flex-row gap-4">
                    VL-ADK
                    <div className="text-sm text-gray-300  font-normal my-auto flex flex-row gap-2">
                        <div
                            className={`w-2 h-2 rounded-full my-auto ${
                                annotationWs.current?.readyState ===
                                WebSocket.OPEN
                                    ? "bg-green-500"
                                    : "bg-red-500"
                            }`}
                        ></div>
                        YOLO Stream
                    </div>
                    <div className="text-sm text-gray-300  font-normal my-auto flex flex-row gap-2">
                        <div
                            className={`w-2 h-2 rounded-full my-auto ${
                                session ? "bg-green-500" : "bg-red-500"
                            }`}
                        ></div>
                        ADK
                    </div>
                </div>
                <div className="flex flex-row gap-4 text-sm font-normal">
                    <button
                        type="button"
                        onClick={() => eStop()}
                        className={`bg-red-700 border-b-3 border-red-800 rounded-sm p-1 px-2 text-white my-auto cursor-pointer duration-100 hover:bg-red-900 shadow-sm`}
                    >
                        EMERGENCY STOP
                    </button>
                    <button
                        type="button"
                        onClick={() => {
                            setSession(null);
                            startSession().then((session) => {
                                setSession(session);
                                console.log(session);
                            });
                        }}
                        className={`bg-green-700 border-b-3 border-green-800 rounded-sm p-1 px-2 text-white my-auto cursor-pointer duration-100 hover:bg-green-900 shadow-sm`}
                    >
                        RESET SESSION
                    </button>
                </div>
            </div>
            <div className="h-full grid grid-cols-12 gap-1 bg-gradient-to-b from-[#364153] to-[#27303e] border-[#27303e] shadow-md border-2 rounded-md p-1">
                {/* Plan Chart - Left side, wider */}
                <div className="col-span-3 flex flex-col gap-1">
                    <div className="text-xs p-1 px-2 border-2 border-green-900 bg-green-900 rounded-sm w-fit">
                        CONTROLS
                    </div>
                    <ManualControls currentPrompts={currentPrompts} />
                </div>

                {/* Video Stream - Middle */}
                <div className="col-span-6 flex flex-col h-full gap-1">
                    <VideoStream
                        image={image}
                        currentPrompts={currentPrompts}
                    />
                </div>

                {/* Chat/Tab section - Right side, narrower */}
                <div className="col-span-3 flex flex-col gap-1">
                    <div className="flex flex-row gap-2 text-xs">
                        <button
                            type="button"
                            onClick={() => setTab(AGENT_GRAPH)}
                            className={`bg-green-700 border-b-3 border-green-800 rounded-sm p-1 px-2 text-white my-auto cursor-pointer duration-100 hover:bg-green-900 ${
                                tab === AGENT_GRAPH
                                    ? "bg-green-900 border-green-900 shadow-none"
                                    : "shadow-sm"
                            }`}
                        >
                            AGENT GRAPH
                        </button>
                        <button
                            type="button"
                            onClick={() => setTab(RADAR)}
                            className={`bg-green-700 border-b-3 border-green-800 rounded-sm p-1 px-2 text-white my-auto cursor-pointer duration-100 hover:bg-green-900 ${
                                tab === RADAR
                                    ? "bg-green-900 border-green-900"
                                    : "shadow-sm"
                            }`}
                        >
                            RADAR
                        </button>
                        <button
                            type="button"
                            onClick={() => setTab(MOTOR_DATA)}
                            className={`bg-green-700 border-b-3 border-green-800 rounded-sm p-1 px-2 text-white my-auto cursor-pointer duration-100 hover:bg-green-900 ${
                                tab === MOTOR_DATA
                                    ? "bg-green-900 border-green-900 shadow-none"
                                    : "shadow-sm"
                            }`}
                        >
                            MOTOR DATA
                        </button>
                    </div>
                    <div className="flex-1">
                        {tab === AGENT_GRAPH && <AgentGraph />}
                        {tab === RADAR && <Radar />}
                        {tab === MOTOR_DATA && (
                            <Motor motorData={motorData} control={control} />
                        )}
                    </div>
                    <div className="flex-1">
                        <Chat session={session} />
                    </div>
                </div>
            </div>
        </div>
    );
}
