import { useState } from 'react';
import { Decision } from '../types';
import RiskBadge from './RiskBadge';
import ConfidenceBadge from './ConfidenceBadge';
import ReasoningTrail from './ReasoningTrail';
import { approveDecision, rejectDecision } from '../lib/api';

type QueueItemProps = {
  decision: Decision;
  onUpdate: () => void;
};

export default function QueueItem({ decision, onUpdate }: QueueItemProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const eventSummary = decision.structured_event?.summary || decision.justification || 'Unknown Event';
  const riskScore = decision.risk_assessment?.overall_risk_score || decision.risk_assessment?.risk_score || 0;

  const handleApprove = async () => {
    setIsSubmitting(true);
    try {
      const res = await approveDecision(decision.id);
      if (res.ok) {
        onUpdate();
      } else {
        alert('Failed to approve decision');
      }
    } catch (error) {
      alert('Failed to approve decision');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!rejectReason.trim()) {
      alert('Please provide a rejection reason.');
      return;
    }
    setIsSubmitting(true);
    try {
      const res = await rejectDecision(decision.id, rejectReason);
      if (res.ok) {
        onUpdate();
      } else {
        alert('Failed to reject decision');
      }
    } catch (error) {
      alert('Failed to reject decision');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getStatusColor = (status: string) => {
    if (status === 'approved') return 'text-success bg-success/10 border-success/20 shadow-glow-success';
    if (status === 'rejected') return 'text-danger bg-danger/10 border-danger/20 shadow-glow-danger';
    return 'text-warning bg-warning/10 border-warning/20';
  };

  return (
    <div className={`bg-zinc-700 shadow-sm border border-zinc-500 rounded-2xl hover:shadow-md transition-all rounded-2xl overflow-hidden border border-zinc-500 hover:border-emerald-600/20 hover:shadow-glow transition-all duration-300 ${
      isExpanded ? 'bg-surface/50 border-emerald-600/25' : ''
    }`}>
      <div className="p-5 sm:p-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5">
          <div className="space-y-4 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <RiskBadge score={riskScore} />
              <ConfidenceBadge score={decision.confidence_score} framing={decision.hitl_framing} />
              
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-lg text-xs font-semibold bg-zinc-800 border border-zinc-500 text-zinc-50 capitalize">
                {decision.action_type}
              </span>
              
              <span className="text-[11px] text-zinc-300 font-medium">
                Review window: {decision.estimated_resolution_days > 0 ? `within ${decision.estimated_resolution_days} days` : 'Immediate'}
              </span>
            </div>
            
            <div>
              <h4 className="text-base sm:text-lg font-bold text-zinc-50 leading-snug group-hover:text-emerald-400 transition-colors">
                {eventSummary}
              </h4>
              <p className="text-xs text-zinc-200 mt-1 max-w-4xl leading-relaxed">
                {decision.justification}
              </p>
            </div>
            
            <div className="flex items-center gap-6 text-xs text-zinc-200">
              <div className="flex items-center gap-1.5">
                <svg className="w-4 h-4 text-zinc-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" /></svg>
                <span className="font-semibold text-zinc-50">Supplier:</span>
                <span>{decision.target_supplier_name}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <svg className="w-4 h-4 text-zinc-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" /></svg>
                <span className="font-semibold text-zinc-50">Product:</span>
                <span>{decision.target_product}</span>
              </div>
            </div>
          </div>
          
          <div className="flex items-center justify-between lg:justify-end gap-3 border-t lg:border-t-0 pt-4 lg:pt-0 border-zinc-500">
            {decision.status !== 'pending' && (
              <span className={`px-3 py-1 rounded-xl text-xs font-bold uppercase border ${getStatusColor(decision.status)}`}>
                {decision.status}
              </span>
            )}
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className={`text-xs font-bold px-4 py-2.5 rounded-xl border transition-all duration-300 flex items-center gap-1.5 ${
                isExpanded 
                  ? 'bg-emerald-500 text-zinc-50 border-emerald-600/50 shadow-glow' 
                  : 'bg-zinc-800 text-zinc-200 border-zinc-500 hover:text-zinc-50 hover:bg-zinc-800 hover:border-zinc-400'
              }`}
            >
              <span>{isExpanded ? 'Collapse' : 'Inspect Risk'}</span>
              <span>{isExpanded ? '▲' : '▼'}</span>
            </button>
          </div>
        </div>

        {isExpanded && (
          <div className="mt-6 border-t border-zinc-500 pt-6 animate-in slide-in-from-top-4 fade-in duration-300">
            <div className="flex items-center gap-2 text-xs font-semibold text-warning bg-warning/5 border border-warning/10 px-3 py-2.5 rounded-xl max-w-fit">
              <svg className="w-4 h-4 text-current" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
              <span>Supervisor loops: {decision.iteration_count} iterations completed</span>
            </div>
            
            <ReasoningTrail decision={decision} />

            {decision.status === 'pending' && (
              <div className="mt-8 border-t border-zinc-500 pt-6 space-y-4">
                <h4 className="text-xs font-bold text-zinc-50 uppercase tracking-widest">Execute Human-in-the-Loop Action</h4>
                
                <div className="flex flex-col md:flex-row gap-3">
                  <button
                    onClick={handleApprove}
                    disabled={isSubmitting}
                    className="flex-1 md:flex-[0.4] bg-gradient-to-r from-success to-emerald-600 hover:from-emerald-500 hover:to-success text-zinc-50 font-bold py-3 px-4 rounded-xl text-sm transition-all duration-300 disabled:opacity-50 flex items-center justify-center gap-2 shadow-[0_0_20px_rgba(16,185,129,0.15)] hover:shadow-[0_0_25px_rgba(16,185,129,0.35)] active:scale-95"
                  >
                    <svg className="w-4 h-4 text-current" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" /></svg>
                    <span>{isSubmitting ? 'Processing...' : 'Approve Recommendation'}</span>
                  </button>
                  
                  <div className="flex-1 flex flex-col sm:flex-row gap-2">
                    <input
                      type="text"
                      placeholder="Specify reason for override rejection (required)..."
                      value={rejectReason}
                      onChange={(e) => setRejectReason(e.target.value)}
                      className="flex-1 bg-[#090d16] border border-zinc-500 hover:border-zinc-500 focus:border-danger/50 rounded-xl px-4 py-3 text-xs text-zinc-50 placeholder:text-zinc-300 focus:outline-none focus:ring-1 focus:ring-danger/30 transition-all duration-300"
                    />
                    <button
                      onClick={handleReject}
                      disabled={isSubmitting || !rejectReason.trim()}
                      className="bg-gradient-to-r from-danger to-rose-600 hover:from-rose-500 hover:to-danger text-zinc-50 font-bold py-3 px-6 rounded-xl text-sm transition-all duration-300 disabled:opacity-30 flex items-center justify-center gap-2 shadow-[0_0_20px_rgba(244,63,94,0.15)] active:scale-95"
                    >
                      <svg className="w-4 h-4 text-current" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
                      <span>Reject</span>
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

