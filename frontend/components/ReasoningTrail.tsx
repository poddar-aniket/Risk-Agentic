import { Decision } from '../types';
import { useState } from 'react';

type ReasoningTrailProps = {
  decision: Decision;
};

export default function ReasoningTrail({ decision }: ReasoningTrailProps) {
  return (
    <div className="mt-8 pt-6 border-t border-zinc-500">
      <h3 className="text-sm font-bold text-emerald-400 tracking-wider uppercase mb-6 flex items-center gap-2">
        <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg> Risk Reasoning Chain
      </h3>
      
      {/* Timeline view */}
      <div className="relative pl-8 space-y-6 border-l-2 border-zinc-500 ml-4">
        
        {/* Step 1: Event */}
        <TrailStep 
          title="Event Detected" 
          icon={<svg className="w-4 h-4 text-zinc-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
          defaultOpen={true}
          data={decision.structured_event}
        >
          {decision.structured_event && (
            <div className="space-y-2 text-xs">
              <div className="flex justify-between items-center bg-zinc-800 p-2 rounded">
                <span className="text-zinc-300">Summary:</span>
                <span className="font-semibold text-zinc-50 text-right">{decision.structured_event.summary}</span>
              </div>
              <div className="text-zinc-200 bg-zinc-800 p-2 rounded leading-normal">
                {decision.structured_event.description}
              </div>
            </div>
          )}
        </TrailStep>

        {/* Step 2: Geo Impact */}
        <TrailStep 
          title="Geo Impact Analysis" 
          icon={<svg className="w-4 h-4 text-zinc-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064" /></svg>}
          data={decision.affected_regions}
        >
          {decision.affected_regions && (
            <div className="space-y-2 text-xs">
              {Array.isArray(decision.affected_regions) ? (
                decision.affected_regions.map((reg: any, i: number) => (
                  <div key={i} className="bg-zinc-800 p-2 rounded flex justify-between items-center">
                    <div>
                      <span className="font-semibold text-zinc-50 block">{reg.region_name || reg.name || 'Region'}</span>
                      <span className="text-zinc-300 text-[10px]">Multiplier: {reg.risk_multiplier || reg.multiplier || 'N/A'}</span>
                    </div>
                    {reg.proximity_miles && (
                      <span className="text-accent-cyan font-medium">{reg.proximity_miles} mi proximity</span>
                    )}
                  </div>
                ))
              ) : (
                <pre className="bg-black/30 p-2 rounded border border-zinc-500 text-[10px] overflow-x-auto text-zinc-200">
                  {JSON.stringify(decision.affected_regions, null, 2)}
                </pre>
              )}
            </div>
          )}
        </TrailStep>

        {/* Step 3: Risk Assessment */}
        <TrailStep 
          title="Risk Assessment" 
          icon={<svg className="w-4 h-4 text-zinc-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>}
          data={decision.risk_assessment}
        >
          {decision.risk_assessment && (
            <div className="space-y-2 text-xs">
              <div className="flex justify-between items-center bg-zinc-800 p-2 rounded">
                <span className="text-zinc-300">Calculated Score:</span>
                <span className="font-bold text-risk-high">{decision.risk_assessment.risk_score || decision.risk_assessment.overall_risk_score}/10</span>
              </div>
              <div className="bg-zinc-800 p-2 rounded leading-normal text-zinc-200">
                <span className="block text-zinc-300 font-semibold mb-1">Justification:</span>
                {decision.risk_assessment.rationale}
              </div>
              {decision.risk_assessment.factors && (
                <div className="bg-zinc-800 p-2 rounded">
                  <span className="block text-zinc-300 font-semibold mb-1">Risk Factors:</span>
                  <ul className="list-disc list-inside space-y-1 text-zinc-200">
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
          icon={<svg className="w-4 h-4 text-zinc-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" /></svg>}
          data={decision.supplier_impact}
        >
          {decision.supplier_impact && (
            <div className="space-y-2 text-xs">
              <div className="grid grid-cols-1 gap-2">
                <div className="bg-zinc-800 p-2 rounded">
                  <span className="block text-zinc-300 mb-0.5">Criticality:</span>
                  <span className="font-bold text-danger capitalize">{decision.supplier_impact.criticality || 'High'}</span>
                </div>
              </div>
            </div>
          )}
        </TrailStep>

        {/* Step 5: Proposal */}
        <TrailStep 
          title="Decision Proposal" 
          icon={<svg className="w-4 h-4 text-zinc-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>}
          data={decision.decision_proposal}
        >
          {decision.decision_proposal && (
            <div className="space-y-2 text-xs">
              <div className="bg-zinc-800 p-2 rounded leading-normal">
                <span className="block text-zinc-300 font-semibold mb-1">Recommended Action:</span>
                <span className="text-zinc-50 font-medium">{decision.decision_proposal.recommended_action || decision.action_type}</span>
              </div>
              <div className="bg-zinc-800 p-2 rounded leading-normal text-zinc-200">
                <span className="block text-zinc-300 font-semibold mb-1">Justification:</span>
                {decision.decision_proposal.justification || decision.justification}
              </div>
            </div>
          )}
        </TrailStep>

        {/* Step 6: Supervisor Review */}
        <TrailStep 
          title={`Supervisor Feedback (Iteration ${decision.iteration_count})`} 
          icon={<svg className="w-4 h-4 text-zinc-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>}
          defaultOpen={true}
          data={decision.supervisor_feedback}
        >
          {decision.supervisor_feedback && (
            <div className="space-y-2 text-xs">
              <div className="flex justify-between items-center bg-zinc-800 p-2 rounded">
                <span className="text-zinc-300">Supervisor Verdict:</span>
                <span className={`font-bold capitalize ${
                  decision.supervisor_feedback.approved ? 'text-success' : 'text-warning'
                }`}>{decision.supervisor_feedback.approved ? 'Approved' : 'Rejected'}</span>
              </div>
              <div className="bg-zinc-800 p-2 rounded leading-normal text-zinc-200">
                <span className="block text-zinc-300 font-semibold mb-1">Supervisor Comments:</span>
                {decision.supervisor_feedback.critique || 'No comments.'}
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
  icon: React.ReactNode; 
  children?: React.ReactNode; 
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  if (!data || Object.keys(data).length === 0) return null;

  return (
    <div className="relative group">
      {/* Visual node on timeline */}
      <span className="absolute -left-12 top-0.5 flex items-center justify-center w-8 h-8 rounded-xl border border-zinc-500 bg-[#0c101a] text-sm group-hover:border-emerald-600/50 group-hover:shadow-glow transition-all duration-300 z-10 select-none">
        {icon}
      </span>

      <div className="bg-zinc-700 shadow-sm border border-zinc-500 rounded-2xl hover:shadow-md transition-all rounded-xl border border-zinc-500 overflow-hidden transition-all duration-300">
        <div 
          onClick={() => setIsOpen(!isOpen)}
          className="flex justify-between items-center px-4 py-3 bg-zinc-800 cursor-pointer hover:bg-zinc-800 hover:bg-zinc-600 transition-colors select-none"
        >
          <span className="text-xs font-semibold text-zinc-50 tracking-wide">{title}</span>
          <span className="text-[10px] text-zinc-300 hover:text-zinc-50 transition-colors flex items-center gap-1">
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
          <div className="p-4 border-t border-zinc-500 space-y-3 bg-zinc-800">
            {children}
            <div className="text-[10px] text-zinc-300 pt-2 border-t border-zinc-500 flex justify-between items-center">
              <span>Source Raw Payload</span>
              <button 
                onClick={(e) => {
                  e.stopPropagation();
                  alert(JSON.stringify(data, null, 2));
                }}
                className="text-emerald-400 hover:underline hover:text-zinc-50"
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

