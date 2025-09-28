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
                stroke={activeAgent === "director" ? "#22c55e" : "#ededed"}
                strokeWidth={activeAgent === "director" ? "3" : "1"}
            >
                <rect
                    x="35%"
                    y="11%"
                    width="30%"
                    height="8%"
                    fill={activeAgent === "director" ? "#16a34a" : "#37415100"}
                    className={
                        activeAgent === "director" ? "animate-pulse" : ""
                    }
                />
                <text
                    x="50%"
                    y="15%"
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
                    x="25%"
                    y="11%"
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
                    x="75%"
                    y="11%"
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
                    x="25%"
                    y="21%"
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
                    x="75%"
                    y="21%"
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
                    y="26%"
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
                y1="30%"
                x2="50%"
                y2="40%"
                stroke="#ededed"
                fill="#ededed"
                strokeWidth="2"
                markerEnd="url(#arrowhead)"
            />

            {/* Loop Container */}
            <g stroke="#ededed" strokeWidth="1" fill="none">
                <line
                    x1="25%"
                    y1="50%"
                    x2="75%"
                    y2="50%"
                    fill="#ededed"
                    fillOpacity="0.0"
                />
                <text
                    x="25%"
                    y="48%"
                    strokeWidth="0"
                    className="fill-[#ededed]"
                    fontSize="12"
                    letterSpacing="0.05em"
                >
                    EXECUTION LOOP
                </text>
            </g>

            {/* Observer Agent */}
            <g
                stroke={activeAgent === "observer" ? "#fbbf24" : "#ededed"}
                strokeWidth={activeAgent === "observer" ? "3" : "1"}
            >
                <rect
                    x="25%"
                    y="53%"
                    width="20%"
                    height="12%"
                    fill={activeAgent === "observer" ? "#d97706" : "#ededed00"}
                    className={
                        activeAgent === "observer" ? "animate-pulse" : ""
                    }
                />
                <text
                    x="35%"
                    y="59%"
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
            </g>

            {/* Pilot Agent */}
            <g
                stroke={activeAgent === "pilot" ? "#f87171" : "#ededed"}
                strokeWidth={activeAgent === "pilot" ? "3" : "1"}
            >
                <rect
                    x="55%"
                    y="53%"
                    width="20%"
                    height="12%"
                    fill={activeAgent === "pilot" ? "#dc2626" : "#37415100"}
                    className={activeAgent === "pilot" ? "animate-pulse" : ""}
                />
                <text
                    x="65%"
                    y="59%"
                    textAnchor="middle"
                    strokeWidth={0.5}
                    dominantBaseline="middle"
                    className={
                        activeAgent === "pilot" ? "fill-white" : "fill-gray-300"
                    }
                >
                    PILOT
                </text>
            </g>

            {/* Loop text */}
            <g>
              <rect
                x="32.5%"
                y="70.5%"
                width="15%"
                height="8%"
                stroke="#ededed"
                fill="#ededed00"
                />
              <text
                  x="40%"
                  y="76%"
                  textAnchor="middle"
                  className="fill-[#ededed]"
                  fontSize="12"
              >
                  UNTIL
              </text>
            </g>
            

            {/* All Tools in 2x3 Grid */}
            <g>
                {/* Row 1: Observer tools */}
                <text
                    x="12%"
                    y="58%"
                    textAnchor="middle"
                    className={
                        activeTool === "view_query"
                            ? "fill-yellow-400 animate-pulse"
                            : "fill-gray-600"
                    }
                    fontSize="12"
                >
                    query
                </text>
                <text
                    x="88%"
                    y="56%"
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
                    x="88%"
                    y="61%"
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
                    x="12%"
                    y="64%"
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
                    x="60%"
                    y="76%"
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
                    x="88%"
                    y="66%"
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
                    markerWidth="2.5"
                    markerHeight="5"
                    refX="2.55"
                    refY="2.5"
                    orient="auto"
                >
                    <polygon points="0 0, 2.5 2.5, 0 5" fill="#ededed" />
                </marker>
            </defs>
        </svg>
    );
}
