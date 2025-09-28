export const wsURL = "ws://127.0.0.1:8890";
export const annotationWsURL = "ws://127.0.0.1:8002";
export const controlWsURL = "ws://127.0.0.1:8890"; // Same as wsURL for now

export type ControlSchema = {
    status: string;
    speed: number;
    duration: number;
};

export type ControlMessage = {
    action: "forward" | "backward" | "left" | "right" | "stop";
    speed?: number;
    linear_velocity?: number;
    angular_velocity?: number;
    duration?: number;
};

export type ImageMessage = {
    type: null;
    image: string;
    left_motor: number;
    right_motor: number;
    control: ControlSchema | null;
};

export type UsefulAnnotationObject = {
    class: string;
    confidence: number;
    center: number[];
}

export type YOLOObject = {
    x: number;
    y: number;
    width: number;
    height: number;
    label: string;
};

export type AnnotationMessage = {
    type: "annotations";
    objects: YOLOObject[];
    timestamp: number;
    current_prompts: string[];
};

export type MotorData = {
    left_motor: number;
    right_motor: number;
};

export type Message = ImageMessage | AnnotationMessage;
