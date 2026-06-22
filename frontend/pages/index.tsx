import { useEffect, useState } from 'react';
import Navbar from '../components/Navbar';
import StatCard from '../components/StatCard';
import { getQueue, triggerPipeline } from '../lib/api';
import { Decision } from '../types';
import Link from 'next/link';

export default function Dashboard() {
  const [queue, setQueue] = useState<Decision[]>([]);
  const [loading, setLoading] = useState(true);
  const [isPipelineRunning, setIsPipelineRunning] = useState(false);

  useEffect(() => {
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
    fetchStats();
    
    // Poll for real-time updates
    const interval = setInterval(fetchStats, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleRunPipeline = async () => {
    setIsPipelineRunning(true);
    try {
      await triggerPipeline();
      const updatedData = await getQueue();
      setQueue(updatedData);
      alert('Pipeline finished successfully');
    } catch (error) {
      alert('Failed to run pipeline');
    } finally {
      setIsPipelineRunning(false);
    }
  };

  const pending = queue.filter(item => item.status === 'pending');
  const highCritical = queue.filter(item => item.status === 'pending' && (item.risk_assessment?.overall_risk_score >= 6));
  const approvedToday = queue.filter(item => item.status === 'approved' && new Date(item.created_at).toDateString() === new Date().toDateString());
  const rejectedToday = queue.filter(item => item.status === 'rejected' && new Date(item.created_at).toDateString() === new Date().toDateString());

  const recentActivity = [...queue].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).slice(0, 5);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        
        {/* Stats Row */}
        <div>
          <h2 className="text-xl font-bold text-text-primary mb-4">System Overview</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard title="Total Pending" value={loading ? '-' : pending.length} />
            <StatCard title="High/Critical Risk" value={loading ? '-' : highCritical.length} highlightColor="amber" />
            <StatCard title="Approved Today" value={loading ? '-' : approvedToday.length} highlightColor="green" />
            <StatCard title="Rejected Today" value={loading ? '-' : rejectedToday.length} highlightColor="red" />
          </div>
        </div>

        {/* Recent Activity */}
        <div>
          <h2 className="text-xl font-bold text-text-primary mb-4">Recent Activity</h2>
          <div className="bg-surface border border-border rounded-lg overflow-hidden shadow-sm">
            {loading ? (
              <div className="p-6 text-center text-text-secondary">Loading activity...</div>
            ) : recentActivity.length === 0 ? (
              <div className="p-6 text-center text-text-secondary">No activity found.</div>
            ) : (
              <ul className="divide-y divide-border">
                {recentActivity.map(item => (
                  <li key={item.id}>
                    <Link href="/queue" className="block p-4 hover:bg-background transition-colors">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-text-primary truncate">
                            {item.structured_event?.summary || item.justification || 'Unknown Event'}
                          </p>
                          <p className="text-xs text-text-secondary mt-1">
                            {item.action_type} • {item.target_supplier_name}
                          </p>
                        </div>
                        <div className="flex items-center gap-3 shrink-0">
                          <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                            item.status === 'pending' ? 'bg-amber-dim/20 text-primary' : 
                            item.status === 'approved' ? 'bg-green-900/30 text-success' : 
                            'bg-red-900/30 text-danger'
                          }`}>
                            {item.status.toUpperCase()}
                          </span>
                          <span className="text-xs text-text-secondary">
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
        <div className="bg-surface border border-border rounded-lg p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-6 shadow-sm border-l-4 border-l-primary">
          <div>
            <h3 className="text-lg font-bold text-text-primary">Trigger Pipeline Manually</h3>
            <p className="text-sm text-text-secondary mt-1 max-w-2xl">
              Fetches latest news and weather, runs all 6 agents, and adds new events to the approval queue. This may take a minute.
            </p>
          </div>
          <button
            onClick={handleRunPipeline}
            disabled={isPipelineRunning}
            className="shrink-0 bg-primary hover:bg-amber-500 text-background font-medium px-6 py-3 rounded-md transition-all duration-200 disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {isPipelineRunning && (
              <svg className="animate-spin h-5 w-5 text-background" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            )}
            {isPipelineRunning ? 'Running Pipeline...' : 'Run Pipeline Now'}
          </button>
        </div>

      </main>
    </div>
  );
}
