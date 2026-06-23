type StatCardProps = {
  title: string;
  value: string | number;
  highlightColor?: 'amber' | 'green' | 'red' | 'default';
};

export default function StatCard({ title, value, highlightColor = 'default' }: StatCardProps) {
  const colorMap = {
    amber: 'text-risk-high drop-shadow-[0_0_10px_rgba(249,115,22,0.25)]',
    green: 'text-success drop-shadow-[0_0_10px_rgba(16,185,129,0.25)]',
    red: 'text-danger drop-shadow-[0_0_10px_rgba(244,63,94,0.25)]',
    default: 'text-primary drop-shadow-[0_0_10px_rgba(99,102,241,0.25)]',
  };

  const glowBorderClass = {
    amber: 'glow-border-warning hover:border-warning/30',
    green: 'glow-border-success hover:border-success/30',
    red: 'glow-border-danger hover:border-danger/30',
    default: 'hover:border-primary/30 hover:shadow-glow',
  };

  const iconMap = {
    amber: '⚠️',
    green: '✅',
    red: '❌',
    default: '📥',
  };

  return (
    <div className={`glass-card p-6 rounded-2xl flex flex-col justify-between relative overflow-hidden ${glowBorderClass[highlightColor]}`}>
      {/* Decorative background glow */}
      <div className="absolute -right-6 -bottom-6 w-20 h-20 rounded-full bg-current opacity-5 blur-xl pointer-events-none"></div>
      
      <div className="flex justify-between items-center">
        <h3 className="text-xs font-bold text-text-secondary uppercase tracking-widest">{title}</h3>
        <span className="text-sm select-none opacity-80">{iconMap[highlightColor]}</span>
      </div>
      
      <p className={`mt-4 text-4xl font-extrabold tracking-tight ${colorMap[highlightColor]}`}>
        {value}
      </p>
    </div>
  );
}

