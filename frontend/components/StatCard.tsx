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
    default: 'text-emerald-400 drop-shadow-[0_0_10px_rgba(99,102,241,0.25)]',
  };

  const glowBorderClass = {
    amber: 'glow-border-warning hover:border-warning/30',
    green: 'glow-border-success hover:border-success/30',
    red: 'glow-border-danger hover:border-danger/30',
    default: 'hover:border-emerald-600/30 hover:shadow-glow',
  };

  const iconMap = {
    amber: <svg className="w-5 h-5 text-current" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>,
    green: <svg className="w-5 h-5 text-current" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" /></svg>,
    red: <svg className="w-5 h-5 text-current" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>,
    default: <svg className="w-5 h-5 text-current" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" /></svg>,
  };

  return (
    <div className={`bg-zinc-700 shadow-sm border border-zinc-500 rounded-2xl hover:shadow-md transition-all p-6 rounded-2xl flex flex-col justify-between relative overflow-hidden ${glowBorderClass[highlightColor]}`}>
      {/* Decorative background glow */}
      <div className="absolute -right-6 -bottom-6 w-20 h-20 rounded-full bg-current opacity-5 blur-xl pointer-events-none"></div>
      
      <div className="flex justify-between items-center">
        <h3 className="text-xs font-bold text-zinc-200 uppercase tracking-widest">{title}</h3>
        <span className="text-sm select-none opacity-80">{iconMap[highlightColor]}</span>
      </div>
      
      <p className={`mt-4 text-4xl font-extrabold tracking-tight ${colorMap[highlightColor]}`}>
        {value}
      </p>
    </div>
  );
}

