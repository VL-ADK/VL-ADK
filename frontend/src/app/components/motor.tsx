import { ControlSchema, MotorData } from "../websocket";

export default function Motor({
    motorData,
    control,
}: {
    motorData: MotorData | null;
    control: ControlSchema | null;
}) {
    return (
        <div className="h-full border-2 border-[#27303e] rounded-md shadow-md bg-[#171717] p-2 text-xs flex flex-col relative">
            {/* Status bar at top */}
            <div className="mb-2 p-1 bg-gray-800 rounded text-center">
                {control
                    ? `${control?.status.toUpperCase()} at ${
                          control?.speed
                      } for ${control?.duration} seconds`
                    : "Awaiting command..."}
            </div>

            {/* Motor data display - takes remaining space */}
            <div className="flex-1 grid grid-cols-2 gap-4">
                <div className="flex flex-col items-center justify-center gap-2">
                    <div className="font-bold text-green-300">Left Motor</div>
                    <div className="text-2xl font-mono bg-gray-800 rounded-sm p-3 w-full text-center">
                        {Intl.NumberFormat("en-US", {
                            minimumSignificantDigits: 4,
                            maximumSignificantDigits: 4,
                        }).format(motorData?.left_motor || 0)}
                    </div>
                </div>
                <div className="flex flex-col items-center justify-center gap-2">
                    <div className="font-bold text-green-300">Right Motor</div>
                    <div className="text-2xl font-mono bg-gray-800 rounded-sm p-3 w-full text-center">
                        {Intl.NumberFormat("en-US", {
                            minimumSignificantDigits: 4,
                            maximumSignificantDigits: 4,
                        }).format(motorData?.right_motor || 0)}
                    </div>
                </div>
            </div>

            {/* JetBot image at bottom */}
            <div className="flex justify-center mt-2">
                <img src="JetBotWire.png" alt="Motor" className="w-32" />
            </div>
        </div>
    );
}
