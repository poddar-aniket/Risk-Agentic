type RiskBadgeProps = {
  score: number;
};

export default function RiskBadge({ score }: RiskBadgeProps) {
  let riskLevel = 'Low';
  let colorClass = 'from-emerald-500/10 to-teal-500/10 text-emerald-400 border-emerald-500/20 shadow-[0_0_12px_rgba(16,185,129,0.1)]';

  if (score >= 8) {
    riskLevel = 'Critical';
    colorClass = 'from-rose-500/15 to-red-600/15 text-rose-400 border-rose-500/30 shadow-[0_0_12px_rgba(244,63,94,0.15)]';
  } else if (score >= 6) {
    riskLevel = 'High';
    colorClass = 'from-orange-500/15 to-amber-600/15 text-orange-400 border-orange-500/30 shadow-[0_0_12px_rgba(249,115,22,0.15)]';
  } else if (score >= 4) {
    riskLevel = 'Medium';
    colorClass = 'from-yellow-500/10 to-amber-500/10 text-yellow-400 border-yellow-500/20 shadow-[0_0_12px_rgba(234,179,8,0.1)]';
  }

  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-gradient-to-r border ${colorClass}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse"></span>
      {riskLevel} Risk: {score}/10
    </span>
  );
}

