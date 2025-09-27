"use client";
import { useEffect, useState } from "react";

export type PlanEntry = {
    desc: string;
    startedAt: Date;
    endedAt: Date;
    status: "pending" | "running" | "completed" | "failed";
}

export function PlanChart() {
    const [plans, setPlans] = useState<PlanEntry[]>([]);

    function addPlan(desc: string) {
        console.log(plans.length);
        setPlans([{ desc: "1", startedAt: new Date(), endedAt: new Date(0), status: "pending" }, { desc: "2", startedAt: new Date(), endedAt: new Date(0), status: "pending" }, ...plans]);
    }

    useEffect(() => {
        addPlan("Plan 1");
    }, []);

    return (
        <div className="w-full h-full bg-[#171717] font-mono">
            Plan Chart
            <div className="flex flex-col gap-2 p-1 overflow-y-scroll justify-end">
                {plans.map((plan, i) => (
                    <div key={i} className="flex flex-col gap-1 border p-1">
                        <div>{plan.desc}</div>
                        <div className="flex flex-row gap-1 text-sm text-gray-500">
                            <div>{plan.startedAt.toISOString()}</div>
                            <div>{plan.endedAt.toISOString()}</div>
                            <div>{plan.status}</div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}