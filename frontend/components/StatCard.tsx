type StatCardProps = {
  title: string;
  value: string | number;
  highlightColor?: 'amber' | 'green' | 'red' | 'default';
};

export default function StatCard({ title, value, highlightColor = 'default' }: StatCardProps) {
  const colorMap = {
    amber: 'text-risk-high',
    green: 'text-success',
    red: 'text-danger',
    default: 'text-text-primary',
  };

  return (
    <div className="bg-surface border border-border p-6 rounded-lg shadow-sm">
      <h3 className="text-sm font-medium text-text-secondary uppercase tracking-wider">{title}</h3>
      <p className={`mt-2 text-3xl font-semibold ${colorMap[highlightColor]}`}>
        {value}
      </p>
    </div>
  );
}
