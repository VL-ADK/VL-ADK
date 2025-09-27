"use client";
import { useEffect, useState } from "react";
import { Tooltip } from "react-tooltip";

export type PlanEntry = {
    desc: string;
    startedAt: Date;
    endedAt: Date;
    status: "pending" | "running" | "completed" | "failed";
}

export function PlanChart() {
    const [plans, setPlans] = useState<PlanEntry[]>([]);

    const statusColors = {
        "pending": "bg-gray-500",
        "running": "bg-yellow-500",
        "completed": "bg-green-500",
        "failed": "bg-red-500",
    }

    function addPlan(desc: string) {
        console.log(plans.length);
        setPlans([{ desc: "Scan the area", startedAt: new Date(), endedAt: new Date(0), status: "completed" }, { desc: "Find a target", startedAt: new Date(), endedAt: new Date(0), status: "pending" }, ...plans]);
    }

    useEffect(() => {
        addPlan("Plan 1");
    }, []);

    return (
        <div className="h-full border-2 border-[#27303e] rounded-md shadow-md bg-[#171717] p-1 text-xs">
            <div className="flex flex-col gap-1 overflow-y-scroll justify-end">
                {plans.map((plan, i) => (
                    <div id={`plan-${i}`} key={i} className="flex flex-col gap-1 border-b-2 rounded-sm bg-[#1f2630] border-[#27303e] p-1">
                        <div>{plan.desc}</div>
                        <div className="flex flex-row gap-1.5 px-0.5 text-xs text-gray-500">
                            <div className={`w-1.5 h-1.5 rounded-full my-auto ${statusColors[plan.status]}`} />
                            <div>{plan.status.toUpperCase()}</div>
                            
                        </div>
                        <Tooltip anchorSelect={`#plan-${i}`} float opacity={0.95}>
                            <div>
                                <div className="font-bold text-base">{plan.desc}</div>
                                <div className="flex flex-row gap-1.5 px-0.5 text-xs mb-2">
                                    <div className={`w-1.5 h-1.5 rounded-full my-auto ${statusColors[plan.status]}`} />
                                    <div>{plan.status.toUpperCase()}</div>
                                </div>
                                <div>Started at {plan.startedAt.toLocaleString()}</div>
                                {plan.endedAt >= new Date() ? <div>Ended at {plan.endedAt.toLocaleString()}</div> : <div>Not ended yet</div>}
                            </div>
                        </Tooltip>
                    </div>
                ))}
            </div>
        </div>
    );
}