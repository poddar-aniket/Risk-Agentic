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
  const riskScore = decision.risk_assessment?.overall_risk_score || 0;

  const handleApprove = async () => {
    setIsSubmitting(true);
    try {
      await approveDecision(decision.id);
      onUpdate();
    } catch (error) {
      alert('Failed to approve');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!rejectReason) {
      alert('Please provide a rejection reason.');
      return;
    }
    setIsSubmitting(true);
    try {
      await rejectDecision(decision.id, rejectReason);
      onUpdate();
    } catch (error) {
      alert('Failed to reject');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-surface border border-border rounded-lg shadow-sm overflow-hidden transition-all duration-200 hover:border-amber-dim">
      <div className="p-4 sm:p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-3 flex-1">
            <div className="flex items-center gap-3 flex-wrap">
              <RiskBadge score={riskScore} />
              <ConfidenceBadge score={decision.confidence_score} framing={decision.hitl_framing} />
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-border text-text-primary">
                {decision.action_type}
              </span>
              <span className="text-xs text-text-secondary">
                Review urgency: {decision.estimated_resolution_days > 0 ? `within ${decision.estimated_resolution_days} days` : 'Immediate'}
              </span>
            </div>
            
            <h4 className="text-lg font-medium text-text-primary line-clamp-1">{eventSummary}</h4>
            
            <div className="text-sm text-text-secondary flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" /></svg>
              <span>Target: {decision.target_supplier_name} — {decision.target_product}</span>
            </div>
          </div>
          
          <div className="flex sm:flex-col justify-between sm:justify-center items-center gap-2">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-text-secondary hover:text-primary transition-colors text-sm font-medium px-4 py-2 bg-background rounded-md border border-border"
            >
              {isExpanded ? 'Collapse' : 'Expand'}
            </button>
          </div>
        </div>

        {isExpanded && (
          <div className="mt-6 animate-in slide-in-from-top-2 fade-in duration-200">
            <div className="mb-4 flex items-center gap-2 text-xs text-amber-500 bg-amber-dim/20 px-3 py-2 rounded">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              Supervisor reviewed {decision.iteration_count} time(s)
            </div>
            
            <ReasoningTrail decision={decision} />

            {decision.status === 'pending' && (
              <div className="mt-8 border-t border-border pt-6 space-y-4">
                <h4 className="text-sm font-semibold text-text-primary">Decision Action</h4>
                <div className="flex flex-col sm:flex-row gap-4">
                  <button
                    onClick={handleApprove}
                    disabled={isSubmitting}
                    className="flex-1 bg-success hover:bg-green-600 text-white font-medium py-2 px-4 rounded-md transition-colors disabled:opacity-50"
                  >
                    {isSubmitting ? 'Processing...' : 'Approve Recommended Action'}
                  </button>
                  <div className="flex-1 flex gap-2">
                    <input
                      type="text"
                      placeholder="Reason for rejection (required)"
                      value={rejectReason}
                      onChange={(e) => setRejectReason(e.target.value)}
                      className="flex-1 bg-background border border-border rounded-md px-3 text-sm text-text-primary focus:outline-none focus:border-danger focus:ring-1 focus:ring-danger"
                    />
                    <button
                      onClick={handleReject}
                      disabled={isSubmitting || !rejectReason}
                      className="bg-danger hover:bg-red-600 text-white font-medium py-2 px-4 rounded-md transition-colors disabled:opacity-50"
                    >
                      Reject
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
