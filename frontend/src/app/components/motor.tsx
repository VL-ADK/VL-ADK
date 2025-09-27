import { ControlSchema, MotorData } from "../websocket";

export default function Motor({motorData, control}: {motorData: MotorData | null, control: ControlSchema | null}) {
    return (
        <div className="h-full border-2 border-[#27303e] rounded-md shadow-md bg-[#171717] p-1 text-xs flex flex-col items-center justify-center relative">
            <div className="absolute top-0 left-0 size-full grid grid-cols-2">
                <div className="mx-auto my-auto font-bold flex flex-col items-center justify-center gap-2">
                    <div>Left</div>
                    <div className="text-lg font-normal bg-gray-800 rounded-sm p-1">{Intl.NumberFormat("en-US", {minimumSignificantDigits: 4, maximumSignificantDigits: 4}).format(motorData?.left_motor || 0)}</div>
                </div>
                <div className="mx-auto my-auto font-bold flex flex-col items-center justify-center gap-2">
                    <div>Right</div>
                    <div className="text-lg font-normal bg-gray-800 rounded-sm p-1">{Intl.NumberFormat("en-US", {minimumSignificantDigits: 4, maximumSignificantDigits: 4}).format(motorData?.right_motor || 0)}</div>
                </div>
            </div>
            <div className="absolute top-0 left-0 p-2">
                {control ? `${control?.status.toUpperCase()} at ${control?.speed} for ${control?.duration} seconds` : "Awaiting command..."}
            </div>
            <img src="JetBotWire.png" alt="Motor" className="w-48" />
        </div>
    )
}