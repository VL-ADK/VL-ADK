"use client";
import { useEffect, useState } from "react";

export function AgentGraph() {
    const [activeAgent, setActiveAgent] = useState<string>("");
    const [activeTool, setActiveTool] = useState<string>("");

    // Listen for agent activity via custom events instead of console interception
    useEffect(() => {
        const handleAgentActivity = (event: CustomEvent) => {
            const { author, toolName } = event.detail;

            if (author) {
                setActiveAgent(author);
                setTimeout(() => setActiveAgent(""), 1500);
            }

            if (toolName) {
                const toolMap: Record<string, string> = {
                    rotate_tool: "rotate",
                    move_forward_tool: "move_forward",
                    move_backward_tool: "move_backward",
                    view_query_tool: "view_query",
                    mission_complete_tool: "mission_complete",
                    scan_environment_tool: "scan_environment",
                    initialize_mission_tool: "initialize_mission",
                };

                const displayName = toolMap[toolName];
                if (displayName) {
                    setActiveTool(displayName);
                    setTimeout(() => setActiveTool(""), 1000);
                }
            }
        };

        window.addEventListener(
            "agentActivity",
            handleAgentActivity as EventListener
        );

        return () => {
            window.removeEventListener(
                "agentActivity",
                handleAgentActivity as EventListener
            );
        };
    }, []);

    return (
        <svg className="size-full border-2 border-[#27303e] rounded-md shadow-md bg-[#171717] p-2 text-xs">
            {/* Director Agent */}
            <g
                stroke={activeAgent === "director" ? "#22c55e" : "#4b5563"}
                strokeWidth={activeAgent === "director" ? "3" : "1"}
            >
                <rect
                    x="35%"
                    y="5%"
                    width="30%"
                    height="8%"
                    fill={activeAgent === "director" ? "#16a34a" : "#374151"}
                    className={
                        activeAgent === "director" ? "animate-pulse" : ""
                    }
                />
                <text
                    x="50%"
                    y="9%"
                    textAnchor="middle"
                    strokeWidth={0.5}
                    dominantBaseline="middle"
                    className={
                        activeAgent === "director"
                            ? "fill-white"
                            : "fill-gray-300"
                    }
                >
                    DIRECTOR
                </text>
            </g>

            {/* Director Tools */}
            <g>
                <text
                    x="35%"
                    y="15%"
                    textAnchor="middle"
                    className={
                        activeTool === "initialize_mission"
                            ? "fill-green-400 animate-pulse"
                            : "fill-gray-600"
                    }
                    fontSize="11"
                >
                    init
                </text>
                <text
                    x="45%"
                    y="15%"
                    textAnchor="middle"
                    className={
                        activeTool === "rotate" && activeAgent === "director"
                            ? "fill-green-400 animate-pulse"
                            : "fill-gray-600"
                    }
                    fontSize="11"
                >
                    rotate
                </text>
                <text
                    x="55%"
                    y="15%"
                    textAnchor="middle"
                    className={
                        activeTool === "move_forward" &&
                        activeAgent === "director"
                            ? "fill-green-400 animate-pulse"
                            : "fill-gray-600"
                    }
                    fontSize="11"
                >
                    move
                </text>
                <text
                    x="65%"
                    y="15%"
                    textAnchor="middle"
                    className={
                        activeTool === "view_query" &&
                        activeAgent === "director"
                            ? "fill-green-400 animate-pulse"
                            : "fill-gray-600"
                    }
                    fontSize="11"
                >
                    view
                </text>
                <text
                    x="50%"
                    y="18%"
                    textAnchor="middle"
                    className={
                        activeTool === "mission_complete" &&
                        activeAgent === "director"
                            ? "fill-green-400 animate-pulse"
                            : "fill-gray-600"
                    }
                    fontSize="11"
                >
                    complete
                </text>
            </g>

            {/* Arrow down */}
            <line
                x1="50%"
                y1="22%"
                x2="50%"
                y2="32%"
                stroke="#10b981"
                strokeWidth="2"
                markerEnd="url(#arrowhead)"
            />

            {/* Loop Container */}
            <g stroke="#4b5563" strokeWidth="1" fill="none">
                <rect
                    x="15%"
                    y="32%"
                    width="70%"
                    height="58%"
                    rx="5"
                    fill="#374151"
                    fillOpacity="0.1"
                />
                <text
                    x="17%"
                    y="37%"
                    className="fill-gray-500"
                    fontSize="10"
                    letterSpacing="0.1em"
                >
                    EXECUTION LOOP
                </text>
            </g>

            {/* Observer Agent */}
            <g
                stroke={activeAgent === "observer" ? "#fbbf24" : "#4b5563"}
                strokeWidth={activeAgent === "observer" ? "3" : "1"}
            >
                <rect
                    x="25%"
                    y="47%"
                    width="20%"
                    height="12%"
                    fill={activeAgent === "observer" ? "#d97706" : "#374151"}
                    className={
                        activeAgent === "observer" ? "animate-pulse" : ""
                    }
                />
                <text
                    x="35%"
                    y="53%"
                    textAnchor="middle"
                    strokeWidth={0.5}
                    dominantBaseline="middle"
                    className={
                        activeAgent === "observer"
                            ? "fill-white"
                            : "fill-gray-300"
                    }
                >
                    OBSERVER
                </text>
                <text
                    x="35%"
                    y="56%"
                    textAnchor="middle"
                    strokeWidth={0.5}
                    dominantBaseline="middle"
                    className={
                        activeAgent === "observer"
                            ? "fill-orange-200"
                            : "fill-gray-500"
                    }
                    fontSize="10"
                >
                    Vision
                </text>
            </g>

            {/* Pilot Agent */}
            <g
                stroke={activeAgent === "pilot" ? "#f87171" : "#4b5563"}
                strokeWidth={activeAgent === "pilot" ? "3" : "1"}
            >
                <rect
                    x="55%"
                    y="47%"
                    width="20%"
                    height="12%"
                    fill={activeAgent === "pilot" ? "#dc2626" : "#374151"}
                    className={activeAgent === "pilot" ? "animate-pulse" : ""}
                />
                <text
                    x="65%"
                    y="53%"
                    textAnchor="middle"
                    strokeWidth={0.5}
                    dominantBaseline="middle"
                    className={
                        activeAgent === "pilot" ? "fill-white" : "fill-gray-300"
                    }
                >
                    PILOT
                </text>
                <text
                    x="65%"
                    y="56%"
                    textAnchor="middle"
                    strokeWidth={0.5}
                    dominantBaseline="middle"
                    className={
                        activeAgent === "pilot"
                            ? "fill-red-200"
                            : "fill-gray-500"
                    }
                    fontSize="10"
                >
                    Movement
                </text>
            </g>

            {/* Loop text */}
            <text
                x="50%"
                y="75%"
                textAnchor="middle"
                className="fill-gray-500"
                fontSize="12"
            >
                Loop Until Complete
            </text>

            {/* All Tools in 2x3 Grid */}
            <g>
                {/* Row 1: Observer tools */}
                <text
                    x="25%"
                    y="80%"
                    textAnchor="middle"
                    className={
                        activeTool === "view_query"
                            ? "fill-yellow-400 animate-pulse"
                            : "fill-gray-600"
                    }
                    fontSize="12"
                >
                    view_query
                </text>
                <text
                    x="50%"
                    y="80%"
                    textAnchor="middle"
                    className={
                        activeTool === "move_forward" && activeAgent === "pilot"
                            ? "fill-red-400 animate-pulse"
                            : "fill-gray-600"
                    }
                    fontSize="12"
                >
                    move
                </text>
                <text
                    x="75%"
                    y="80%"
                    textAnchor="middle"
                    className={
                        activeTool === "rotate" && activeAgent === "pilot"
                            ? "fill-red-400 animate-pulse"
                            : "fill-gray-600"
                    }
                    fontSize="12"
                >
                    rotate
                </text>

                {/* Row 2: More tools */}
                <text
                    x="25%"
                    y="87%"
                    textAnchor="middle"
                    className={
                        activeTool === "scan_environment" &&
                        activeAgent === "pilot"
                            ? "fill-red-400 animate-pulse"
                            : "fill-gray-600"
                    }
                    fontSize="12"
                >
                    scan
                </text>
                <text
                    x="50%"
                    y="87%"
                    textAnchor="middle"
                    className={
                        activeTool === "mission_complete" &&
                        (activeAgent === "observer" || activeAgent === "pilot")
                            ? "fill-yellow-400 animate-pulse"
                            : "fill-gray-600"
                    }
                    fontSize="12"
                >
                    complete
                </text>
                <text
                    x="75%"
                    y="87%"
                    textAnchor="middle"
                    className="fill-gray-600"
                    fontSize="12"
                >
                    stop
                </text>
            </g>

            {/* Arrow marker definition */}
            <defs>
                <marker
                    id="arrowhead"
                    markerWidth="10"
                    markerHeight="7"
                    refX="10"
                    refY="3.5"
                    orient="auto"
                >
                    <polygon points="0 0, 10 3.5, 0 7" fill="#10b981" />
                </marker>
            </defs>
        </svg>
    );
}
