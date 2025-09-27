import Image from "next/image";

export const F_WIDTH = 1640
const F_HEIGHT = 1232

export type YOLOObject = {
    x: number;
    y: number;
    width: number;
    height: number;
    label: string;
}

export function VideoStream({ image, yoloObjects }: { image: string | undefined, yoloObjects: YOLOObject[] }) {
    // turn base64 string into image url
    const imageUrl = image != "" ? `data:image/jpeg;base64,${image}` : "";
    //<img className="h-full w-auto rounded-md shadow-md border-2 border-[#27303e]" src="static.gif"/>
    return (
        <div className={`size-full relative`}>
            <svg className="size-full absolute top-0 left-0">
                {yoloObjects.map((obj, i) => (
                    <g key={"yolo_"+i}>
                        <rect x={`${Math.floor(obj.x/F_WIDTH*100)}%`} y={`${Math.floor(obj.y/F_HEIGHT*100)}%`} width={`${Math.floor(obj.width/F_WIDTH*100)}%`} height={`${Math.floor(obj.height/F_HEIGHT*100)}%`} stroke="red" fill="none" strokeWidth={1} />
                        <rect x={`${Math.floor(obj.x/F_WIDTH*100)}%`} y={`${Math.floor(obj.y/F_HEIGHT*100) - 2}%`} width={`5%`} height={`2%`} stroke="none" fill="red" fillOpacity={0.5} />
                        <text x={`${Math.floor(obj.x/F_WIDTH*100)}%`} y={`${Math.floor(obj.y/F_HEIGHT*100)}%`} fill="white" fontSize="16">{obj.label}</text>
                    </g>
                ))}
            </svg>
            <div className="size-full absolute top-0 left-0">
                <div className="flex flex-row p-1 gap-1 text-sm">
                    <div className="p-1 bg-[#171717]/75 rounded-lg text-white w-fit">FRONT</div>
                    <div className="p-1 bg-[#171717]/75 rounded-lg text-white w-fit">BACK</div>
                </div>
            </div>
            {image != "" ? (
                <img className="object-cover w-full h-full rounded-md" src={imageUrl} alt="Video Stream" />
            ) : (
                <img className="h-full w-full rounded-md shadow-md border-2 border-[#27303e]" src="static.gif"/>
            )}
        </div>
    );
}