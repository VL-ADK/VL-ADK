"use client";
import Image from "next/image";
import { VideoStream } from "./components/videostream";
import { Chat } from "./components/chat";
import { Radar } from "./components/radar";
import { AgentGraph } from "./components/agentgraph";
import { PlanChart } from "./components/planchart";
import { Message, MotorData, wsURL } from "./websocket";
import { useEffect, useRef, useState } from "react";

export default function Home() {
  const ws = useRef<WebSocket | null>(null);
  const [image, setImage] = useState<string | undefined>("WIN_20250926_23_02_58_Pro.jpg");
  const [control, setControl] = useState<MotorData | null>(null);

  function connectWS() {
    try {
      ws.current = new WebSocket(wsURL);

      ws.current.onopen = () => {
        console.log("Connected to server");
      }

      ws.current.onmessage = (event) => {
        const body:Message = JSON.parse(event.data);
        //console.log(body);
        console.log(body);
        setImage(body.image);
        setControl({left_motor: body.left_motor, right_motor: body.right_motor});
      }

      ws.current.onerror = (event) => {
         console.log(event);
      }

      ws.current.onclose = () => {
        console.log("Disconnected from server, retrying in 5 seconds...");
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
  }, []);

  return (
    <div className="h-dvh w-dvw flex flex-col gap-2 border">
      <div className="text-2xl font-bold w-full border p-2">VL-ADK</div>
      <div className="h-full border p-2 flex flex-row gap-2">
        <div className="border flex flex-col h-full gap-2">
          <VideoStream image={image}/>
          <Chat/>
        </div>
        <div className="size-full border flex flex-row gap-2">
          <div className="size-full flex flex-col justify-between gap-2">
            <Radar/>
            <PlanChart/>
          </div>
          <AgentGraph/>
        </div>
      </div>
    </div>
  );
}
