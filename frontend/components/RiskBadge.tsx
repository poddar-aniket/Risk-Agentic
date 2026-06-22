type RiskBadgeProps = {
  score: number;
};

export default function RiskBadge({ score }: RiskBadgeProps) {
  let riskLevel = 'Low';
  let colorClass = 'bg-risk-low text-background';

  if (score >= 8) {
    riskLevel = 'Critical';
    colorClass = 'bg-risk-critical text-background';
  } else if (score >= 6) {
    riskLevel = 'High';
    colorClass = 'bg-risk-high text-background';
  } else if (score >= 4) {
    riskLevel = 'Medium';
    colorClass = 'bg-risk-medium text-background';
  }

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${colorClass}`}>
      {riskLevel} Risk: {score}/10
    </span>
  );
}
