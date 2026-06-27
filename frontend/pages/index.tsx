import { useEffect, useState } from 'react';
import Navbar from '../components/Navbar';
import StatCard from '../components/StatCard';
import { getQueue } from '../lib/api';
import { Decision } from '../types';
import Link from 'next/link';
import { usePipeline } from '../lib/PipelineContext';

export default function Dashboard() {
  const [queue, setQueue] = useState<Decision[]>([]);
  const [loading, setLoading] = useState(true);
  const { isPipelineRunning, runPipeline } = usePipeline();

  const fetchStats = async () => {
    try {
      const data = await getQueue();
      setQueue(data);
    } catch (error) {
      console.error('Failed to fetch queue', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    
    // Poll for real-time updates
    const interval = setInterval(fetchStats, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleRunPipeline = async () => {
    const success = await runPipeline();
    if (success) {
      fetchStats();
    }
  };

  const pending = queue.filter(item => item.status === 'pending');
  const highCritical = queue.filter(item => item.status === 'pending' && (item.risk_assessment?.overall_risk_score >= 6 || item.risk_assessment?.risk_score >= 6));
  const approvedTotal = queue.filter(item => item.status === 'approved');
  const rejectedTotal = queue.filter(item => item.status === 'rejected');

  const recentActivity = [...queue]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5);

  return (
    <div className="min-h-screen bg-zinc-800">
      <Navbar />
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-10">
        
        {/* Welcome / Ambient Banner */}
        <div className="relative bg-zinc-700 shadow-sm border border-zinc-500 p-6 sm:p-8 rounded-3xl overflow-hidden">
          <div className="absolute -right-20 -top-20 w-80 h-80 rounded-full bg-emerald-500/10 blur-3xl pointer-events-none"></div>
          <div className="absolute -left-20 -bottom-20 w-80 h-80 rounded-full bg-emerald-500/10 blur-3xl pointer-events-none"></div>
          
          <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="space-y-2">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-bold tracking-widest text-emerald-400 bg-emerald-500/10 border border-emerald-600/20 uppercase">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span> Risk Monitoring active
              </span>
              <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-zinc-50 leading-tight">
                Supply Chain Risk Operations
              </h1>
              <p className="text-sm text-zinc-200 max-w-2xl leading-relaxed">
                Autonomous multi-agent risk assessment monitoring events, geo impact, supplier tiering, and supervisor approvals.
              </p>
            </div>
            
            <div className="shrink-0 flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-success animate-ping"></span>
              <span className="text-xs font-semibold text-zinc-200 uppercase tracking-wider">All Systems Operational</span>
            </div>
          </div>
        </div>

        {/* Stats Row */}
        <div>
          <h2 className="text-xs font-bold text-zinc-200 uppercase tracking-widest mb-4">System Live Overview</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard title="Total Pending Review" value={loading ? '-' : pending.length} />
            <StatCard title="High/Critical Risk" value={loading ? '-' : highCritical.length} highlightColor="amber" />
            <StatCard title="Total Approved" value={loading ? '-' : approvedTotal.length} highlightColor="green" />
            <StatCard title="Total Rejected" value={loading ? '-' : rejectedTotal.length} highlightColor="red" />
          </div>
        </div>

        {/* Recent Activity */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xs font-bold text-zinc-200 uppercase tracking-widest">Recent Activity Log</h2>
            <Link href="/queue" className="text-xs font-bold text-emerald-400 hover:text-zinc-50 transition-colors">
              View Entire Queue →
            </Link>
          </div>
          
          <div className="bg-zinc-700 shadow-sm border border-zinc-500 rounded-2xl overflow-hidden">
            {loading ? (
              <div className="p-12 text-center text-sm text-zinc-200 flex flex-col items-center justify-center gap-3">
                <div className="w-6 h-6 border-2 border-t-transparent border-emerald-600 rounded-full animate-spin"></div>
                <span>Retrieving active logs...</span>
              </div>
            ) : recentActivity.length === 0 ? (
              <div className="p-12 text-center text-sm text-zinc-200 bg-zinc-800">
                No recent activity registered in the database.
              </div>
            ) : (
              <ul className="divide-y divide-white/5">
                {recentActivity.map(item => (
                  <li key={item.id} className="hover:bg-zinc-800 transition-colors duration-200">
                    <Link href="/queue" className="block p-4 sm:p-5">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                        <div className="flex-1 min-w-0 space-y-1">
                          <p className="text-sm font-bold text-zinc-50 truncate">
                            {item.structured_event?.summary || item.justification || 'Unknown Event'}
                          </p>
                          <p className="text-xs text-zinc-200 flex items-center gap-2 flex-wrap">
                            <span className="bg-zinc-800 px-2 py-0.5 rounded text-[10px] uppercase font-semibold border border-zinc-500">{item.action_type}</span>
                            <span>•</span>
                            <span className="font-semibold text-zinc-50">{item.target_supplier_name}</span>
                            <span>•</span>
                            <span>{item.target_product}</span>
                          </p>
                        </div>
                        <div className="flex items-center gap-4 shrink-0 justify-between sm:justify-end">
                          <span className={`px-2.5 py-0.5 text-[10px] font-bold rounded-lg uppercase border ${
                            item.status === 'pending' ? 'bg-warning/10 text-warning border-warning/20' : 
                            item.status === 'approved' ? 'bg-success/10 text-success border-success/20' : 
                            'bg-danger/10 text-danger border-danger/20'
                          }`}>
                            {item.status}
                          </span>
                          <span className="text-xs text-zinc-300 font-medium">
                            {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {/* Pipeline Trigger */}
        <div className="bg-zinc-700 shadow-sm border border-zinc-500 rounded-2xl p-6 sm:p-8 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-6 shadow-glow border border-emerald-600/20 relative overflow-hidden bg-gradient-to-r from-primary/5 to-transparent">
          {/* Accent decoration */}
          <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-primary to-emerald-400"></div>
          
          <div className="space-y-1.5">
            <h3 className="text-base sm:text-lg font-bold text-zinc-50 flex items-center gap-2">
              <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg> Trigger News & Threat Intelligence Pipeline
            </h3>
            <p className="text-xs text-zinc-200 max-w-3xl leading-relaxed">
              Fetches global news APIs and weather forecasts, runs all 6 agents sequentially, and runs supervisor consensus checking. Evaluated risks will append to the queue.
            </p>
          </div>
          
          <button
            onClick={handleRunPipeline}
            disabled={isPipelineRunning}
            className="shrink-0 relative overflow-hidden bg-emerald-500 hover:bg-emerald-500-hover text-zinc-900 font-bold px-6 py-3.5 rounded-xl text-sm transition-all duration-300 shadow-glow disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 border border-emerald-600/30 active:scale-95"
          >
            {isPipelineRunning ? (
              <>
                <svg className="animate-spin h-4 w-4 text-zinc-50" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>Pipeline Running...</span>
              </>
            ) : (
              <span>Run Pipeline Now</span>
            )}
          </button>
        </div>

      </main>
    </div>
  );
}

