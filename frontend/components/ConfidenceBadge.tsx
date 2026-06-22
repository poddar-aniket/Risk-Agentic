type ConfidenceBadgeProps = {
  score: number;
  framing: 'high_confidence' | 'low_confidence';
};

export default function ConfidenceBadge({ score, framing }: ConfidenceBadgeProps) {
  const isHigh = score >= 7 || framing === 'high_confidence';
  const bgColor = isHigh ? 'bg-success' : 'bg-primary';
  const text = isHigh ? 'High Confidence — Recommended' : 'Low Confidence — Please Review';

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold text-background ${bgColor}`}>
      {text} ({score}/10)
    </span>
  );
}
