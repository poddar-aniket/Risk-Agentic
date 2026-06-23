import { Decision } from '../types';
import { useState } from 'react';

type ReasoningTrailProps = {
  decision: Decision;
};

export default function ReasoningTrail({ decision }: ReasoningTrailProps) {
  return (
    <div className="mt-8 pt-6 border-t border-white/5">
      <h3 className="text-sm font-bold text-primary tracking-wider uppercase mb-6 flex items-center gap-2">
        <span>🔍</span> Risk Reasoning Chain
      </h3>
      
      {/* Timeline view */}
      <div className="relative pl-8 space-y-6 border-l-2 border-white/5 ml-4">
        
        {/* Step 1: Event */}
        <TrailStep 
          title="Event Detected" 
          icon="🚨" 
          defaultOpen={true}
          data={decision.structured_event}
        >
          {decision.structured_event && (
            <div className="space-y-2 text-xs">
              <div className="flex justify-between items-center bg-white/5 p-2 rounded">
                <span className="text-text-muted">Summary:</span>
                <span className="font-semibold text-text-primary text-right">{decision.structured_event.summary}</span>
              </div>
              <div className="text-text-secondary bg-white/5 p-2 rounded leading-normal">
                {decision.structured_event.description}
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-white/5 p-2 rounded">
                  <span className="block text-text-muted mb-0.5">Sentiment:</span>
                  <span className={`font-bold capitalize ${
                    decision.structured_event.sentiment === 'negative' ? 'text-danger' : 'text-success'
                  }`}>{decision.structured_event.sentiment}</span>
                </div>
                <div className="bg-white/5 p-2 rounded">
                  <span className="block text-text-muted mb-0.5">Relevance:</span>
                  <span className="font-bold text-primary">{decision.structured_event.relevance_score}/10</span>
                </div>
              </div>
            </div>
          )}
        </TrailStep>

        {/* Step 2: Geo Impact */}
        <TrailStep 
          title="Geo Impact Analysis" 
          icon="🌍" 
          data={decision.affected_regions}
        >
          {decision.affected_regions && (
            <div className="space-y-2 text-xs">
              {Array.isArray(decision.affected_regions) ? (
                decision.affected_regions.map((reg: any, i: number) => (
                  <div key={i} className="bg-white/5 p-2 rounded flex justify-between items-center">
                    <div>
                      <span className="font-semibold text-text-primary block">{reg.region_name || reg.name || 'Region'}</span>
                      <span className="text-text-muted text-[10px]">Multiplier: {reg.risk_multiplier || reg.multiplier || 'N/A'}</span>
                    </div>
                    {reg.proximity_miles && (
                      <span className="text-accent-cyan font-medium">{reg.proximity_miles} mi proximity</span>
                    )}
                  </div>
                ))
              ) : (
                <pre className="bg-black/30 p-2 rounded border border-white/5 text-[10px] overflow-x-auto text-text-secondary">
                  {JSON.stringify(decision.affected_regions, null, 2)}
                </pre>
              )}
            </div>
          )}
        </TrailStep>

        {/* Step 3: Risk Assessment */}
        <TrailStep 
          title="Risk Assessment" 
          icon="📊" 
          data={decision.risk_assessment}
        >
          {decision.risk_assessment && (
            <div className="space-y-2 text-xs">
              <div className="flex justify-between items-center bg-white/5 p-2 rounded">
                <span className="text-text-muted">Calculated Score:</span>
                <span className="font-bold text-risk-high">{decision.risk_assessment.risk_score || decision.risk_assessment.overall_risk_score}/10</span>
              </div>
              <div className="bg-white/5 p-2 rounded leading-normal text-text-secondary">
                <span className="block text-text-muted font-semibold mb-1">Justification:</span>
                {decision.risk_assessment.justification}
              </div>
              {decision.risk_assessment.factors && (
                <div className="bg-white/5 p-2 rounded">
                  <span className="block text-text-muted font-semibold mb-1">Risk Factors:</span>
                  <ul className="list-disc list-inside space-y-1 text-text-secondary">
                    {Array.isArray(decision.risk_assessment.factors) ? (
                      decision.risk_assessment.factors.map((f: string, i: number) => <li key={i}>{f}</li>)
                    ) : (
                      <li>{String(decision.risk_assessment.factors)}</li>
                    )}
                  </ul>
                </div>
              )}
            </div>
          )}
        </TrailStep>

        {/* Step 4: Supplier Impact */}
        <TrailStep 
          title="Supplier Impact" 
          icon="🏭" 
          data={decision.supplier_impact}
        >
          {decision.supplier_impact && (
            <div className="space-y-2 text-xs">
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-white/5 p-2 rounded">
                  <span className="block text-text-muted mb-0.5">Tier:</span>
                  <span className="font-bold text-accent-purple">Tier {decision.supplier_impact.tier || decision.supplier_impact.supplier_tier || 'N/A'}</span>
                </div>
                <div className="bg-white/5 p-2 rounded">
                  <span className="block text-text-muted mb-0.5">Criticality:</span>
                  <span className="font-bold text-danger capitalize">{decision.supplier_impact.criticality || 'High'}</span>
                </div>
              </div>
              <div className="bg-white/5 p-2 rounded flex justify-between items-center">
                <span className="text-text-muted">Exposure Score:</span>
                <span className="font-bold text-primary">{decision.supplier_impact.exposure_score || 'N/A'}/10</span>
              </div>
            </div>
          )}
        </TrailStep>

        {/* Step 5: Proposal */}
        <TrailStep 
          title="Decision Proposal" 
          icon="💡" 
          data={decision.decision_proposal}
        >
          {decision.decision_proposal && (
            <div className="space-y-2 text-xs">
              <div className="bg-white/5 p-2 rounded leading-normal">
                <span className="block text-text-muted font-semibold mb-1">Recommended Action:</span>
                <span className="text-text-primary font-medium">{decision.decision_proposal.recommended_action || decision.action_type}</span>
              </div>
              <div className="bg-white/5 p-2 rounded leading-normal text-text-secondary">
                <span className="block text-text-muted font-semibold mb-1">Justification:</span>
                {decision.decision_proposal.justification || decision.justification}
              </div>
            </div>
          )}
        </TrailStep>

        {/* Step 6: Supervisor Review */}
        <TrailStep 
          title={`Supervisor Feedback (Iteration ${decision.iteration_count})`} 
          icon="👁️" 
          defaultOpen={true}
          data={decision.supervisor_feedback}
        >
          {decision.supervisor_feedback && (
            <div className="space-y-2 text-xs">
              <div className="flex justify-between items-center bg-white/5 p-2 rounded">
                <span className="text-text-muted">Supervisor Verdict:</span>
                <span className={`font-bold capitalize ${
                  decision.supervisor_feedback.decision_status === 'approved' ? 'text-success' : 'text-warning'
                }`}>{decision.supervisor_feedback.decision_status}</span>
              </div>
              <div className="bg-white/5 p-2 rounded leading-normal text-text-secondary">
                <span className="block text-text-muted font-semibold mb-1">Supervisor Comments:</span>
                {decision.supervisor_feedback.feedback || decision.supervisor_feedback.justification || 'No comments.'}
              </div>
            </div>
          )}
        </TrailStep>

      </div>
    </div>
  );
}

function TrailStep({ 
  title, 
  data, 
  defaultOpen = false, 
  icon, 
  children 
}: { 
  title: string; 
  data: any; 
  defaultOpen?: boolean; 
  icon: string; 
  children?: React.ReactNode; 
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  if (!data || Object.keys(data).length === 0) return null;

  return (
    <div className="relative group">
      {/* Visual node on timeline */}
      <span className="absolute -left-12 top-0.5 flex items-center justify-center w-8 h-8 rounded-xl border border-white/10 bg-[#0c101a] text-sm group-hover:border-primary/50 group-hover:shadow-glow transition-all duration-300 z-10 select-none">
        {icon}
      </span>

      <div className="glass-card rounded-xl border border-white/5 overflow-hidden transition-all duration-300">
        <div 
          onClick={() => setIsOpen(!isOpen)}
          className="flex justify-between items-center px-4 py-3 bg-white/[0.02] cursor-pointer hover:bg-white/[0.04] transition-colors select-none"
        >
          <span className="text-xs font-semibold text-text-primary tracking-wide">{title}</span>
          <span className="text-[10px] text-text-muted hover:text-text-primary transition-colors flex items-center gap-1">
            {isOpen ? (
              <>
                Hide <span>▲</span>
              </>
            ) : (
              <>
                Show details <span>▼</span>
              </>
            )}
          </span>
        </div>
        
        {isOpen && (
          <div className="p-4 border-t border-white/5 space-y-3 bg-black/10">
            {children}
            <div className="text-[10px] text-text-muted pt-2 border-t border-white/5 flex justify-between items-center">
              <span>Source Raw Payload</span>
              <button 
                onClick={(e) => {
                  e.stopPropagation();
                  alert(JSON.stringify(data, null, 2));
                }}
                className="text-primary hover:underline hover:text-white"
              >
                Inspect JSON
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

