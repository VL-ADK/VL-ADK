"use client";

import { useEffect, useRef, useState } from "react";
import { baseUrl, sendPrompt, SessionToken } from "../endpoints";
import { Loader, Send } from "lucide-react";

export type Message = {
    role: "user" | "agent";
    content: string;
}

function buildMessage(message: string) {
    return { role: "agent", content: message } as Message;
}

export function Chat({session}: {session: SessionToken | null}) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [loading, setLoading] = useState(false);
    const [canSend, setCanSend] = useState(false);

    const decoder = new TextDecoder('utf-8');

    const inputRef = useRef<HTMLInputElement>(null);

    const evtSource = useRef<EventSource | null>(null);

    const handleSendMessage = async (message: string) => {
        if(!session) {
            console.log("No session");
            return;
        }

        const usr = { role: "user", content: message } as Message;

        setMessages([...messages, usr]);
        setLoading(true);
        const stream = await sendPrompt(session, message);
        const prompt:any[] = []
        const reader = stream.getReader();
        reader.read().then(function pump({done, value}):any {

            function parse(p:any[]) {
                try {
                    let agentFeedback: Message[] = [];
                    p.forEach((o:any)=>{
                        if(!o.partial)
                        o.content.parts.forEach((part:any)=>{
                            if(part.text != null)
                            {
                                agentFeedback.push(buildMessage(part.text));
                                setMessages([...messages, usr, ...agentFeedback]);
                            }
                                
                            if(part.functionCall != null)
                            {
                                let res =`Called (${part.functionCall.name}): `;
                                /*
                                (part.functionCall.args as any[]).forEach((arg:any)=>{
                                    res += arg.toString() + " ";
                                })
                                */
                                agentFeedback.push(buildMessage(res));
                                setMessages([...messages, usr, ...agentFeedback]);
                            }
        
                            if(part.functionResponse != null)
                            {
                                let res =`Recieved (${part.functionResponse.name}): `;
                                /*
                                (part.functionResponse.response as any[]).forEach((arg:any)=>{
                                    res += arg.toString() + " ";
                                })
                                    */
                                agentFeedback.push(buildMessage(res));
                                setMessages([...messages, usr, ...agentFeedback]);
                            }
                        })
                    })
                } catch (error) {
                    console.log("Error parsing response:", error);
                }
            }

            if(done) {
                return;
            }
            prompt.push(JSON.parse(decoder.decode(value).replace("data: ", "").replace("\n", "")));
            parse(prompt);
            return reader.read().then(pump);
        });
        
        setLoading(false);
    }

    useEffect(()=>{
        const chatMessages = document.getElementById("chat-messages");
        if(chatMessages) {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    },[messages])

    useEffect(()=>{
        setMessages([]);
        if(inputRef.current) {
            inputRef.current.value = "";
        }
        setCanSend(false);
    },[session])

    return (
        <div className="h-full border-2 border-[#27303e] rounded-md shadow-md bg-[#171717] flex flex-col justify-end gap-2 p-2 text-xs">
            <div id="chat-messages" className="w-full max-h-[160px] bg-[#171717] flex flex-col gap-2 overflow-auto">
            {messages.map((message, index) => (
                <div 
                    key={index} 
                    className={`flex ${message.role === "user"? "justify-end" : "justify-start"}`}
                >
                    <div 
                        className={`max-w-64 text-wrap wrap-break-word overflow-x-hidden px-2 py-1 rounded-sm shadow-sm ${
                            message.role === "user" 
                                ? "bg-green-700 text-white" 
                                : "bg-gray-800 text-white"
                        }`}
                    >
                        {message.content}
                    </div>
                </div>))}
                {loading && <div 
                    className={`w-fit px-2 py-1 rounded-sm shadow-sm bg-gray-800 text-white`}
                    >
                        <Loader className="animate-spin w-4 h-4 my-auto text-white" />
                    </div>}
            </div>
            <form className="h-fit w-full bg-[#171717] flex flex-row gap-2" onSubmit={(e) => {
                if(!canSend) {
                    e.preventDefault();
                    return;
                }
                e.preventDefault();
                handleSendMessage(inputRef.current?.value || "");
                if(inputRef.current) {
                    inputRef.current.value = "";
                    setCanSend(false);
                }
            }}>
                <input onChange={(e) => setCanSend(session != null && (e.target.value.replace(/\s/g, "") !== ""))} type="text" className="size-full px-2 border bg-[#171717] p-1 text-xs rounded-sm border-gray-700" placeholder="Send a prompt" ref={inputRef} />
                <button type="submit" className={`size-full border bg-[#171717] cursor-pointer w-fit p-1 px-1 rounded-sm text-sm ${canSend ? "border-white" : "border-gray-700"}`}>
                    <Send className={`w-4 h-4 my-auto ${canSend ? "text-white" : "text-gray-700"}`} />
                </button>
            </form>
        </div>
    );
}