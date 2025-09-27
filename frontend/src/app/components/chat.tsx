"use client";

import { useEffect, useRef, useState } from "react";

export type Message = {
    role: "user" | "agent";
    content: string;
}

export function Chat() {
    const [messages, setMessages] = useState<Message[]>([]);

    const handleSendMessage = (message: string) => {
        setMessages([...messages, { role: "user", content: message }]);
    }

    useEffect(()=>{
        const chatMessages = document.getElementById("chat-messages");
        if(chatMessages) {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    },[messages])

    const inputRef = useRef<HTMLInputElement>(null);

    return (
        <div className="h-full border border-yellow-500 bg-black flex flex-col justify-end gap-2 p-2">
            <div id="chat-messages" className="w-full max-h-[260px] bg-black flex flex-col gap-2 overflow-auto">
            {messages.map((message, index) => (
                <div 
                    key={index} 
                    className={`flex ${message.role === "user"? "justify-end" : "justify-start"}`}
                >
                    <div 
                        className={`max-w-64 text-wrap wrap-break-word overflow-x-hidden px-2 py-1 rounded-lg text-sm ${
                            message.role === "user" 
                                ? "bg-blue-500 text-white" 
                                : "bg-gray-200 text-black"
                        }`}
                    >
                        {message.content}
                    </div>
                </div>))}
            </div>
            <form className="h-fit w-full bg-black flex flex-row gap-2" onSubmit={(e) => {
                if(inputRef.current?.value.replace(/\s/g, "") === "") {
                    e.preventDefault();
                    return;
                }
                e.preventDefault();
                handleSendMessage(inputRef.current?.value || "");
                if(inputRef.current) {
                    inputRef.current.value = "";
                }
            }}>
                <input type="text" className="size-full border bg-black p-1 text-sm" ref={inputRef} />
                <button type="submit" className="size-full border bg-black cursor-pointer w-fit p-1 text-sm">Send</button>
            </form>
        </div>
    );
}