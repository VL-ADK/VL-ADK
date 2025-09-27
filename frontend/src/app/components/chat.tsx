"use client";

import { useEffect, useRef, useState } from "react";
import { sendPrompt, SessionToken } from "../endpoints";
import { Loader, Send } from "lucide-react";

export type Message = {
    role: "user" | "agent";
    content: string;
}

export function Chat({session}: {session: SessionToken | null}) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [loading, setLoading] = useState(false);
    const [canSend, setCanSend] = useState(false);

    const inputRef = useRef<HTMLInputElement>(null);

    const handleSendMessage = async (message: string) => {
        if(!session) {
            console.log("No session");
            return;
        }

        setMessages([...messages, { role: "user", content: message }]);
        setLoading(true);
        const prompt = await sendPrompt(session, message);
        console.log(prompt);
        setLoading(false);
        try {
            setMessages([...messages, { role: "user", content: message }, { role: "agent", content: prompt[0].content.parts[0].text }]);
        } catch (error) {
            console.log("Error parsing response:", error);
        }
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
            <div id="chat-messages" className="w-full max-h-full bg-[#171717] flex flex-col gap-2 overflow-auto">
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
                    className={`w-fit px-2 py-1 rounded-sm shadow-sm bg-gray-200 text-black`}
                    >
                        <Loader className="animate-spin w-4 h-4 my-auto" />
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