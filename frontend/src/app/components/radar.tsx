"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { UsefulAnnotationObject } from "../websocket";

interface RadarProps {
  data: UsefulAnnotationObject[];
}

export function Radar({ data }: RadarProps) {
  const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042", "red", "pink"];
  const [chartData, setChartData] = useState<Object[]>([]);
  useEffect(() => {
    const genData = () => {
      const counts = new Map<string, number>();

      for (const item of data) {
        counts.set(item.class, (counts.get(item.class) || 0) + 1);
      }

      const cData = Array.from(counts.entries()).map(([name, count]) => ({
        name,
        count,
      }));
      setChartData(cData);
    };
    genData();
  }, [data]);
  return (
    <ResponsiveContainer
      className="h-full border-2 border-[#27303e] rounded-md shadow-md bg-[#171717] p-2 text-xs flex flex-col relative"
      width="100%"
    >
      <BarChart
        data={chartData}
        margin={{ top: 20, right: 30, left: 20, bottom: 10 }}
      >
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis allowDecimals={false} />
        <Tooltip />
        <Bar dataKey="count" animationDuration={500}>
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
          {/* Show value labels above bars */}
          <LabelList dataKey="count" position="top" />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
