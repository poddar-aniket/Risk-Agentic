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
    setLoading(true);
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
      const score = item.risk_assessment?.risk_score || 0;
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
        const scoreA = a.risk_assessment?.risk_score || 0;
        const scoreB = b.risk_assessment?.risk_score || 0;
        return scoreB - scoreA;
      }
      if (sortBy === 'urgency') {
        return a.estimated_resolution_days - b.estimated_resolution_days;
      }
      return 0;
    });

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col md:flex-row gap-8">
        
        {/* Sidebar Filters */}
        <aside className="w-full md:w-64 shrink-0 space-y-6">
          <div>
            <h3 className="text-sm font-semibold text-text-primary mb-3">Status</h3>
            <div className="flex flex-col gap-2">
              {['all', 'pending', 'approved', 'rejected'].map(status => (
                <label key={status} className="flex items-center gap-2 cursor-pointer">
                  <input 
                    type="radio" 
                    name="status" 
                    className="text-primary focus:ring-primary bg-background border-border"
                    checked={statusFilter === status} 
                    onChange={() => setStatusFilter(status as any)} 
                  />
                  <span className="text-sm text-text-secondary capitalize">{status}</span>
                </label>
              ))}
            </div>
          </div>
          
          <div>
            <h3 className="text-sm font-semibold text-text-primary mb-3">Risk Score</h3>
            <div className="flex flex-col gap-2">
              {[
                { value: 'all', label: 'All' },
                { value: 'critical', label: 'Critical (8-10)' },
                { value: 'high', label: 'High (6-7)' },
                { value: 'medium', label: 'Medium (4-5)' },
                { value: 'low', label: 'Low (1-3)' },
              ].map(risk => (
                <label key={risk.value} className="flex items-center gap-2 cursor-pointer">
                  <input 
                    type="radio" 
                    name="risk" 
                    className="text-primary focus:ring-primary bg-background border-border"
                    checked={riskFilter === risk.value} 
                    onChange={() => setRiskFilter(risk.value as any)} 
                  />
                  <span className="text-sm text-text-secondary">{risk.label}</span>
                </label>
              ))}
            </div>
          </div>
          
          <div>
            <h3 className="text-sm font-semibold text-text-primary mb-3">Sort By</h3>
            <select 
              className="w-full bg-surface border border-border rounded-md text-sm text-text-primary p-2 focus:ring-1 focus:ring-primary outline-none"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
            >
              <option value="urgency">Review Urgency</option>
              <option value="highest_risk">Highest Risk</option>
              <option value="newest">Newest</option>
            </select>
          </div>
        </aside>

        {/* Main Content */}
        <div className="flex-1 space-y-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-text-primary">Approval Queue</h1>
            <span className="text-sm text-text-secondary">{filteredQueue.length} items</span>
          </div>

          {loading ? (
            <div className="text-center py-12 text-text-secondary">Loading queue...</div>
          ) : filteredQueue.length === 0 ? (
            <div className="text-center py-12 text-text-secondary bg-surface border border-border rounded-lg">
              No decisions found matching the current filters.
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
