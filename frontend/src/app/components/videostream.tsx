import Image from "next/image";

export function VideoStream({ image }: { image: string | undefined }) {
    // turn base64 string into image url
    const imageUrl = image ? `data:image/jpeg;base64,${image}` : "";

    return (
        <div className="w-108 h-fit border border-blue-500 relative">
            <div className="size-full absolute top-0 left-0">
                <div className="flex flex-row p-1 gap-1">
                    <div className="p-1 bg-black/75 rounded-lg text-white w-fit">Front</div>
                    <div className="p-1 bg-black/75 rounded-lg text-white w-fit">Back</div>
                </div>
            </div>
            <img className="object-cover w-full h-full" src={imageUrl} alt="Video Stream" />
        </div>
    );
}