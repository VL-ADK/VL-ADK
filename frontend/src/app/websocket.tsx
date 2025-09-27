export const wsURL = "ws://127.0.0.1:8890";

export type ControlSchema = {
    status: string;
    speed: number;
    duration: number;
}

export type AllMessage = {
    type: null;
    "image": string;
    "left_motor": number;
    "right_motor": number;
    "control": ControlSchema | null;
}

export type MotorData = {
    "left_motor": number;
    "right_motor": number;
}

export type Message = AllMessage;