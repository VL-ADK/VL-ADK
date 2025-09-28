export const F_WIDTH = 1640;
const F_HEIGHT = 1232;

export type YOLOObject = {
    x: number;
    y: number;
    width: number;
    height: number;
    label: string;
};

export function VideoStream({
    image,
    currentPrompts,
}: {
    image: string | undefined;
    currentPrompts: string[];
}) {
    // turn base64 string into image url
    const imageUrl = image != "" ? `data:image/jpeg;base64,${image}` : "";
    //<img className="h-full w-auto rounded-md shadow-md border-2 border-[#27303e]" src="static.gif"/>
    return (
        <div className={`size-full relative`}>
            <div className="size-full absolute top-0 left-0">
                <div className="flex flex-row p-1 gap-1 text-sm">
                    {currentPrompts.length > 0 && (
                        <div className="p-1 bg-[#171717]/75 rounded-lg text-white w-fit">
                            PROMPTS: {currentPrompts.join(", ")}
                        </div>
                    )}
                </div>
            </div>
            {image != "" ? (
                <img
                    className="object-cover w-full h-full rounded-md"
                    src={imageUrl}
                    alt="Video Stream"
                />
            ) : (
                <img
                    className="h-full w-full rounded-md shadow-md border-2 border-[#27303e]"
                    src="static.gif"
                />
            )}
        </div>
    );
}
