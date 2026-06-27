import { useEffect, useState } from 'react';
import Navbar from '../components/Navbar';
import QueueItem from '../components/QueueItem';
import { getQueue } from '../lib/api';
import { Decision } from '../types';

export default function QueuePage() {
  const [queue, setQueue] = useState<Decision[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Filters
  const [statusFilter, setStatusFilter] = useState<'all' | 'pending' | 'approved' | 'rejected'>('pending');
  const [riskFilter, setRiskFilter] = useState<'all' | 'critical' | 'high' | 'medium' | 'low'>('all');
  const [sortBy, setSortBy] = useState<'newest' | 'highest_risk' | 'urgency'>('urgency');

  const fetchQueue = async () => {
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
    fetchQueue();
    
    // Poll for real-time updates
    const interval = setInterval(fetchQueue, 3000);
    return () => clearInterval(interval);
  }, []);

  const filteredQueue = queue
    .filter(item => statusFilter === 'all' || item.status === statusFilter)
    .filter(item => {
      if (riskFilter === 'all') return true;
      const score = item.risk_assessment?.risk_score || item.risk_assessment?.overall_risk_score || 0;
      if (riskFilter === 'critical') return score >= 8;
      if (riskFilter === 'high') return score >= 6 && score < 8;
      if (riskFilter === 'medium') return score >= 4 && score < 6;
      if (riskFilter === 'low') return score < 4;
      return true;
    })
    .sort((a, b) => {
      if (sortBy === 'newest') {
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      }
      if (sortBy === 'highest_risk') {
        const scoreA = a.risk_assessment?.risk_score || a.risk_assessment?.overall_risk_score || 0;
        const scoreB = b.risk_assessment?.risk_score || b.risk_assessment?.overall_risk_score || 0;
        return scoreB - scoreA;
      }
      if (sortBy === 'urgency') {
        return a.estimated_resolution_days - b.estimated_resolution_days;
      }
      return 0;
    });

  return (
    <div className="min-h-screen bg-zinc-800">
      <Navbar />
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 flex flex-col lg:flex-row gap-8">
        
        {/* Sidebar Filters */}
        <aside className="w-full lg:w-72 shrink-0 space-y-6">
          <div className="bg-zinc-700 shadow-sm border border-zinc-500 rounded-2xl p-6 space-y-6">
            <div>
              <h2 className="text-xs font-bold text-emerald-400 uppercase tracking-widest mb-4">Filters</h2>
              <h3 className="text-xs font-bold text-zinc-200 uppercase tracking-widest mb-3">Status</h3>
              <div className="flex flex-col gap-2.5">
                {['all', 'pending', 'approved', 'rejected'].map(status => (
                  <label key={status} className="flex items-center gap-3 cursor-pointer group">
                    <input 
                      type="radio" 
                      name="status" 
                      className="w-4 h-4 text-emerald-400 focus:ring-emerald-600/40 bg-zinc-700 border-zinc-500 checked:bg-emerald-500"
                      checked={statusFilter === status} 
                      onChange={() => setStatusFilter(status as any)} 
                    />
                    <span className={`text-sm transition-colors capitalize ${
                      statusFilter === status 
                        ? 'text-zinc-50 font-semibold' 
                        : 'text-zinc-200 group-hover:text-zinc-50'
                    }`}>
                      {status}
                    </span>
                  </label>
                ))}
              </div>
            </div>
            
            <div className="border-t border-zinc-500 pt-5">
              <h3 className="text-xs font-bold text-zinc-200 uppercase tracking-widest mb-3">Risk Assessment</h3>
              <div className="flex flex-col gap-2.5">
                {[
                  { value: 'all', label: 'All Risks' },
                  { value: 'critical', label: 'Critical (8-10)' },
                  { value: 'high', label: 'High (6-7)' },
                  { value: 'medium', label: 'Medium (4-5)' },
                  { value: 'low', label: 'Low (1-3)' },
                ].map(risk => (
                  <label key={risk.value} className="flex items-center gap-3 cursor-pointer group">
                    <input 
                      type="radio" 
                      name="risk" 
                      className="w-4 h-4 text-emerald-400 focus:ring-emerald-600/40 bg-zinc-700 border-zinc-500 checked:bg-emerald-500"
                      checked={riskFilter === risk.value} 
                      onChange={() => setRiskFilter(risk.value as any)} 
                    />
                    <span className={`text-sm transition-colors ${
                      riskFilter === risk.value 
                        ? 'text-zinc-50 font-semibold' 
                        : 'text-zinc-200 group-hover:text-zinc-50'
                    }`}>
                      {risk.label}
                    </span>
                  </label>
                ))}
              </div>
            </div>
            
            <div className="border-t border-zinc-500 pt-5">
              <h3 className="text-xs font-bold text-zinc-200 uppercase tracking-widest mb-3">Sort Priorities</h3>
              <select 
                className="w-full bg-zinc-700 border border-zinc-500 rounded-xl text-xs text-zinc-50 px-3 py-2.5 focus:border-emerald-600/50 outline-none transition-all duration-300 font-semibold cursor-pointer"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
              >
                <option value="urgency">Review Urgency</option>
                <option value="highest_risk">Highest Risk Assessment</option>
                <option value="newest">Newest Events</option>
              </select>
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <div className="flex-1 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-widest">Active Queue</span>
              <h1 className="text-2xl font-extrabold text-zinc-50">Decision Approval Desk</h1>
            </div>
            <span className="text-xs font-bold text-zinc-200 bg-zinc-800 border border-zinc-500 px-3 py-1.5 rounded-xl">
              {filteredQueue.length} {filteredQueue.length === 1 ? 'item' : 'items'} found
            </span>
          </div>

          {loading ? (
            <div className="text-center py-16 text-sm text-zinc-200 flex flex-col items-center justify-center gap-3">
              <div className="w-8 h-8 border-2 border-t-transparent border-emerald-600 rounded-full animate-spin"></div>
              <span>Connecting to database...</span>
            </div>
          ) : filteredQueue.length === 0 ? (
            <div className="text-center py-16 text-sm text-zinc-200 bg-zinc-800 shadow-sm border border-zinc-500 rounded-2xl">
              <span className="block text-2xl mb-2">📁</span>
              <span>No decision entries match current filter parameters.</span>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredQueue.map(item => (
                <QueueItem key={item.id} decision={item} onUpdate={fetchQueue} />
              ))}
            </div>
          )}
        </div>
        
      </main>
    </div>
  );
}

