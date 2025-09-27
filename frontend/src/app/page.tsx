"use client";
import Image from "next/image";
import { VideoStream } from "./components/videostream";
import { Chat } from "./components/chat";
import { Radar } from "./components/radar";
import { AgentGraph } from "./components/agentgraph";
import { PlanChart } from "./components/planchart";
import { Message, MotorData, wsURL } from "./websocket";
import { useEffect, useRef, useState } from "react";
import { SessionToken, startSession } from "./endpoints";

export default function Home() {
  const ws = useRef<WebSocket | null>(null);
  const [image, setImage] = useState<string | undefined>("");
  const [control, setControl] = useState<MotorData | null>(null);
  const [session, setSession] = useState<SessionToken | null>(null);

  const AGENT_GRAPH = 0;
  const RADAR = 1;
  const MOTOR_DATA = 2;

  const [tab, setTab] = useState<number>(AGENT_GRAPH);

  function connectWS() {
    try {
      ws.current = new WebSocket(wsURL);

      ws.current.onopen = () => {
        console.log("Connected to server");
      }

      ws.current.onmessage = (event) => {
        const body:Message = JSON.parse(event.data);
        //console.log(body);
        setImage(body.image);
        setControl({left_motor: body.left_motor, right_motor: body.right_motor});
      }

      ws.current.onerror = (event) => {
         console.log(event);
      }

      ws.current.onclose = () => {
        console.log("Disconnected from server, retrying in 5 seconds...");
        setImage("");
        setTimeout(() => {
          connectWS();
        }, 5000);
      }
    } catch (error) {
      console.log(error);
    }
  }

  useEffect(() => {
    connectWS();
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
            <div className={`w-2 h-2 rounded-full my-auto ${ws.current?.readyState === WebSocket.OPEN ? "bg-green-500" : "bg-red-500"}`}></div>
            WebSocket
          </div>
          <div className="text-sm text-gray-300  font-normal my-auto flex flex-row gap-2">
            <div className={`w-2 h-2 rounded-full my-auto ${session ? "bg-green-500" : "bg-red-500"}`}></div>
            ADK
          </div>
        </div>
        <div className="flex flex-row gap-4 text-sm font-normal">
          <button type="button" className={`bg-red-800 border-b-2 border-red-700 rounded-sm p-1 px-2 text-white my-auto cursor-pointer duration-100 hover:bg-red-900 shadow-sm`}>
            EMERGENCY STOP
          </button>
          <button type="button" onClick={() => {
            setSession(null);
            startSession().then((session) => {
              setSession(session);
              console.log(session);
            });
          }} className={`bg-green-800 border-b-2 border-green-700 rounded-sm p-1 px-2 text-white my-auto cursor-pointer duration-100 hover:bg-green-900 shadow-sm`}>
            RESET SESSION
          </button>
        </div>
      </div>
      <div className="h-full grid grid-cols-2 gap-1 bg-gradient-to-b from-[#364153] to-[#27303e] border-[#27303e] shadow-md border-2 rounded-md p-1">
        <div className="flex flex-col h-full gap-1 col-span-1">
          <VideoStream image={image}/>
        </div>
        <div className="size-full grid grid-cols-3 gap-1">
          <div className="col-span-2 grid grid-rows-3 gap-1">
            <div className="row-span-2 flex flex-col gap-1 size-full">
              <div className="flex flex-row gap-2 text-xs">
                <button type="button" onClick={() => setTab(AGENT_GRAPH)} className={`bg-green-800 border-b-2 border-green-700 rounded-sm p-1 px-2 text-white my-auto cursor-pointer duration-100 hover:bg-green-900 ${tab === AGENT_GRAPH ? "bg-green-900 border-green-900 shadow-none" : "shadow-sm"}`}>
                  AGENT GRAPH
                </button>
                <button type="button" onClick={() => setTab(RADAR)} className={`bg-green-800 border-b-2 border-green-700 rounded-sm p-1 px-2 text-white my-auto cursor-pointer duration-100 hover:bg-green-900 ${tab === RADAR ? "bg-green-900 border-green-900" : "shadow-sm"}`}>
                  RADAR
                </button>
                <button type="button" onClick={() => setTab(MOTOR_DATA)} className={`bg-green-800 border-b-2 border-green-700 rounded-sm p-1 px-2 text-white my-auto cursor-pointer duration-100 hover:bg-green-900 ${tab === MOTOR_DATA ? "bg-green-900 border-green-900 shadow-none" : "shadow-sm"}`}>
                  MOTOR DATA
                </button>
              </div>
              <div className="size-full">
                {tab === AGENT_GRAPH && <AgentGraph/>}
                {tab === RADAR && <Radar/>}
                {tab === MOTOR_DATA && <PlanChart/>}
              </div>
            </div>
            <div className="row-span-1 size-full">
              <Chat session={session}/>
            </div>
          </div>
          <div className="flex flex-col gap-1">
            <div className="text-xs p-1 px-2 border-2 border-green-900 bg-green-900 rounded-sm w-fit">
              PLAN CHART
            </div>
            <PlanChart/>
          </div>
        </div>
      </div>
    </div>
  );
}
