export const wsURL = "ws://127.0.0.1:8890";

export type ImageMessage = {
    type: "image";
    data: string;
}

export type MotorMessage = {
    type: "control";
    data: {
        "left_motor": number;
        "right_motor": number;
    };
}

export type AllMessage = {
    type: null;
    "image": string;
    "left_motor": number;
    "right_motor": number;
}

export type MotorData = {
    "left_motor": number;
    "right_motor": number;
}

export type Message = AllMessage;