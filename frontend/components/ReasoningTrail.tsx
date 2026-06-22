import { Decision } from '../types';
import { useState } from 'react';

type ReasoningTrailProps = {
  decision: Decision;
};

export default function ReasoningTrail({ decision }: ReasoningTrailProps) {
  return (
    <div className="mt-6 border-t border-border pt-6">
      <h3 className="text-sm font-semibold text-text-primary mb-4">Reasoning Trail</h3>
      <div className="space-y-6 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-border before:to-transparent">
        
        {/* Event */}
        <TrailStep title="Event Detected" data={decision.structured_event} defaultOpen={true} icon="🚨" />
        
        {/* Geo Impact */}
        <TrailStep title="Geo Impact Analysis" data={decision.affected_regions} icon="🌍" />
        
        {/* Risk Assessment */}
        <TrailStep title="Risk Assessment" data={decision.risk_assessment} icon="📊" />
        
        {/* Supplier Mapping */}
        <TrailStep title="Supplier Impact" data={decision.supplier_impact} icon="🏭" />
        
        {/* Decision Proposal */}
        <TrailStep title="Decision Proposal" data={decision.decision_proposal} icon="💡" />
        
        {/* Supervisor Review */}
        <TrailStep title={`Supervisor Review (Iteration ${decision.iteration_count})`} data={decision.supervisor_feedback} defaultOpen={true} icon="👁️" />
        
      </div>
    </div>
  );
}

function TrailStep({ title, data, defaultOpen = false, icon }: { title: string, data: any, defaultOpen?: boolean, icon: string }) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  if (!data || Object.keys(data).length === 0) return null;

  return (
    <div className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
      <div className="flex items-center justify-center w-10 h-10 rounded-full border border-border bg-surface text-text-primary shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10">
        {icon}
      </div>
      <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] p-4 rounded border border-border bg-surface shadow">
        <div className="flex items-center justify-between cursor-pointer" onClick={() => setIsOpen(!isOpen)}>
          <div className="font-semibold text-text-primary text-sm">{title}</div>
          <button className="text-text-secondary hover:text-text-primary transition-colors text-xs">
            {isOpen ? 'Collapse' : 'Expand'}
          </button>
        </div>
        {isOpen && (
          <div className="mt-3 text-sm text-text-secondary">
            <pre className="whitespace-pre-wrap overflow-x-auto p-2 bg-background rounded border border-border text-xs">
              {JSON.stringify(data, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
