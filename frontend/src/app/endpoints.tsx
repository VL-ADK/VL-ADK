export const baseUrl = "http://localhost:8000";
export const ROOT_AGENT = "root_agent";

export type SessionToken = {
    id: string;
    appName: string;
    userId: string;
    state: any;
    events: any[];
    lastUpdateTime: number;
};

export const startSession = async () => {
    const response = await fetch(`${baseUrl}/apps/${ROOT_AGENT}/users/${crypto.randomUUID()}/sessions`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "accept": "application/json",
        },
    });
    return response.json() as Promise<SessionToken>;
};

export const sendPrompt = async (session:SessionToken, prompt: string) => {
    const response = await fetch(`${baseUrl}/run_sse`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ 
            app_name: session.appName,
            user_id: session.userId,
            session_id: session.id,
            new_message: {
                "role": "user",
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            },
            streaming: true
        }),
    });
    console.log(response);
    return response.body as ReadableStream<Uint8Array>;
};

export const eStop = async () => {
    try {
        await fetch(`http://localhost:8889/stop/`, {
            method: "POST",
        });
    } catch (error) {
        // Ignore CORS and other network errors
        console.log("eStop request completed (CORS errors ignored)");
    }
}