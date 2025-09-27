export function AgentGraph() {
  return (
    <svg className="w-full h-full bg-[#171717] font-mono">
        <g stroke="white" strokeWidth="2" className="fill-white">
            <rect x="42.5%" y="11.5%" width="15%" height="6.5%" fill="transparent" />
            <text x="50%" y="15%" textAnchor="middle" strokeWidth={0.5} dominantBaseline="middle">ROOT</text>
        </g>
        <g stroke="white" strokeWidth="2" className="fill-white">
            <rect x="40%" y="26.5%" width="20%" height="6.5%" fill="transparent" />
            <text x="50%" y="30%" textAnchor="middle" strokeWidth={0.5} dominantBaseline="middle">PLANNER</text>
        </g>
    </svg>
  );
}