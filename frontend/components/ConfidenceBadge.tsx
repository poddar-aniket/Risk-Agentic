type ConfidenceBadgeProps = {
  score: number;
  framing: 'high_confidence' | 'low_confidence';
};

export default function ConfidenceBadge({ score, framing }: ConfidenceBadgeProps) {
  const isHigh = score >= 7 || framing === 'high_confidence';
  const colorClass = isHigh 
    ? 'from-indigo-500/10 to-primary/10 text-indigo-300 border-indigo-500/30 shadow-[0_0_12px_rgba(99,102,241,0.15)]' 
    : 'from-amber-500/10 to-warning/10 text-amber-300 border-amber-500/30 shadow-[0_0_12px_rgba(251,191,36,0.15)]';
  const text = isHigh ? 'High Confidence — Recommended' : 'Low Confidence — Review Required';

  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-gradient-to-r border ${colorClass}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse"></span>
      {text} ({score}/10)
    </span>
  );
}

