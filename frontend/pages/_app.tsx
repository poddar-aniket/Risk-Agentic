import "@/styles/globals.css";
import type { AppProps } from "next/app";
import { useEffect, useRef } from "react";
import { PipelineProvider, usePipeline } from "@/lib/PipelineContext";

const NODES = [
  { id: 'event_extraction', label: 'Event Extraction Agent', icon: '🚨', desc: 'Parses article feeds & extracts structured events' },
  { id: 'geo', label: 'Geospatial Impact Agent', icon: '🌍', desc: 'Maps geographic metadata & proximity alerts' },
  { id: 'risk_analysis', label: 'Risk Analysis Agent', icon: '📊', desc: 'Calculates risk scores & evaluates severity factors' },
  { id: 'supplier', label: 'Supplier Mapping Agent', icon: '🏭', desc: 'Links events to supply network tiers & products' },
  { id: 'decision', label: 'Decision Proposal Agent', icon: '💡', desc: 'Drafts operational and mitigation decisions' },
  { id: 'supervisor', label: 'Consensus Supervisor Agent', icon: '👁️', desc: 'Checks score thresholds & commands revision loops' }
];

function GlobalPipelineUI() {
  const { isPipelineRunning, pipelineError, activeNode, pipelineLogs, closeVisualizer } = usePipeline();
  const consoleRef = useRef<HTMLDivElement>(null);

  // Auto-scroll the terminal logs console to the bottom when new logs arrive
  useEffect(() => {
    if (consoleRef.current) {
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
    }
  }, [pipelineLogs]);

  if (!isPipelineRunning) return null;

  const getNodeState = (nodeId: string) => {
    if (pipelineError) {
      return activeNode === nodeId ? 'failed' : 'pending';
    }
    if (activeNode === 'completed') return 'completed';
    if (!activeNode) return 'pending';

    const order = ['ingesting', 'start', 'event_extraction', 'geo', 'risk_analysis', 'supplier', 'decision', 'supervisor'];
    const activeIdx = order.indexOf(activeNode);
    const nodeIdx = order.indexOf(nodeId);

    if (activeIdx === -1) return 'pending';
    if (nodeIdx === activeIdx) return 'active';
    if (nodeIdx < activeIdx) return 'completed';
    return 'pending';
  };

  const getStatusText = () => {
    if (pipelineError) return "PIPELINE EXECUTION INTERRUPTED";
    if (activeNode === 'completed') return "PIPELINE SUCCESS - LOGGED";
    if (activeNode === 'ingesting') return "INGESTING ACTIVE FEEDS...";
    if (activeNode === 'start') return "THREAT IDENTIFIED - RUNNING AGENTS...";
    if (activeNode === 'supervisor') return "SUPERVISOR AUDITING STAGE...";
    return "AGENT CONFLICT RESOLUTION RUNNING...";
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-md p-4 overflow-y-auto transition-all duration-300">
      <div className="glass-panel-heavy p-6 sm:p-8 rounded-3xl border border-white/10 max-w-5xl w-full shadow-glow flex flex-col gap-6 animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header bar */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 border-b border-white/5 pb-4">
          <div>
            <span className="text-[10px] font-bold text-primary uppercase tracking-widest flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full bg-current ${pipelineError ? 'text-danger' : activeNode === 'completed' ? 'text-success' : 'text-primary animate-ping'}`}></span>
              LangGraph Orchestration Monitor
            </span>
            <h3 className="text-lg font-extrabold text-white mt-1 tracking-tight">{getStatusText()}</h3>
          </div>
          
          {(activeNode === 'completed' || pipelineError) && (
            <button
              onClick={closeVisualizer}
              className={`text-xs font-bold px-4 py-2 rounded-xl transition-all duration-300 active:scale-95 ${
                pipelineError 
                  ? 'bg-danger hover:bg-rose-500 text-white shadow-glow-danger' 
                  : 'bg-success hover:bg-emerald-500 text-white shadow-glow-success'
              }`}
            >
              Close Monitor Console
            </button>
          )}
        </div>

        {/* Workspace: Graph & Terminal side-by-side */}
        <div className="flex flex-col lg:flex-row gap-6">
          
          {/* Left panel: Node Visualizer Graph */}
          <div className="flex-1 space-y-4">
            <h4 className="text-[11px] font-bold text-text-secondary uppercase tracking-wider">Multi-Agent Sequence Graph</h4>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 relative">
              {NODES.map((node, idx) => {
                const state = getNodeState(node.id);
                
                const borderClass = 
                  state === 'active' ? 'border-primary bg-primary/10 shadow-glow' : 
                  state === 'completed' ? 'border-success/30 bg-success/5 text-text-secondary' : 
                  state === 'failed' ? 'border-danger bg-danger/10 shadow-glow-danger' : 
                  'border-white/5 bg-white/[0.01] opacity-35';
                
                return (
                  <div 
                    key={node.id}
                    className={`relative p-4 rounded-2xl border transition-all duration-300 flex items-start gap-3.5 ${borderClass}`}
                  >
                    {/* Node status bullet */}
                    <div className="mt-0.5 relative shrink-0">
                      {state === 'completed' ? (
                        <span className="text-success text-sm font-bold">✓</span>
                      ) : state === 'failed' ? (
                        <span className="text-danger text-sm font-bold">✗</span>
                      ) : state === 'active' ? (
                        <span className="relative flex h-3.5 w-3.5">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                          <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-primary"></span>
                        </span>
                      ) : (
                        <div className="w-3.5 h-3.5 rounded-full border border-white/20"></div>
                      )}
                    </div>

                    <div className="min-w-0">
                      <h5 className={`text-xs font-bold flex items-center gap-1.5 ${
                        state === 'active' ? 'text-white' : 
                        state === 'completed' ? 'text-success' : 
                        state === 'failed' ? 'text-danger' : 'text-text-muted'
                      }`}>
                        <span>{node.icon}</span>
                        <span>{node.label}</span>
                      </h5>
                      <p className="text-[10px] text-text-secondary mt-1 leading-normal">
                        {node.desc}
                      </p>
                    </div>

                    {/* Step indexing number */}
                    <span className="absolute top-3 right-3 text-[10px] font-bold opacity-20 font-mono">
                      0{idx + 1}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Loop-back arrow illustration helper */}
            <div className="text-[10px] text-text-muted text-center pt-2 italic flex items-center justify-center gap-1.5">
              <span>💡 Proposal Agent</span>
              <span className="text-primary font-bold">⇄</span>
              <span>👁️ Supervisor Audit</span>
              <span className="text-text-secondary">(dynamic loopback occurs if confidence &lt; 7.0/10)</span>
            </div>
          </div>

          {/* Right panel: Terminal Logs Monitor Console */}
          <div className="w-full lg:w-96 flex flex-col gap-3">
            <h4 className="text-[11px] font-bold text-text-secondary uppercase tracking-wider">Active Execution Output</h4>
            
            <div 
              ref={consoleRef}
              className="w-full h-80 lg:h-[320px] bg-black/60 border border-white/5 rounded-2xl p-4 font-mono text-[10px] leading-relaxed text-emerald-400/90 overflow-y-auto flex flex-col gap-2 shadow-inner"
            >
              {pipelineLogs.map((log, idx) => {
                let colorClass = "text-emerald-400";
                if (log.includes("[System]")) colorClass = "text-accent-cyan";
                if (log.includes("failed") || log.includes("Error") || log.includes("failed:")) colorClass = "text-danger";
                if (log.includes("successfully") || log.includes("persisted")) colorClass = "text-success";
                if (log.includes("[supervisor]")) colorClass = "text-warning";

                return (
                  <div key={idx} className={colorClass}>
                    <span className="text-text-muted select-none mr-1.5">&gt;</span>
                    {log}
                  </div>
                );
              })}
              
              {/* Spinner if running */}
              {!pipelineError && activeNode !== 'completed' && (
                <div className="text-primary flex items-center gap-2 mt-1 animate-pulse">
                  <span className="text-text-muted select-none">&gt;</span>
                  <svg className="animate-spin h-3.5 w-3.5 text-primary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span>Awaiting agent response...</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Warning banner in footer if error occurred */}
        {pipelineError && (
          <div className="bg-danger/10 border border-danger/20 rounded-xl p-3.5 flex items-start gap-2.5">
            <span className="text-danger text-sm">⚠️</span>
            <div className="text-xs">
              <span className="font-bold text-text-primary block">Execution Terminated</span>
              <span className="text-text-secondary leading-normal">{pipelineError}</span>
            </div>
          </div>
        )}
        
      </div>
    </div>
  );
}

export default function App({ Component, pageProps }: AppProps) {
  return (
    <PipelineProvider>
      <div className="min-h-screen flex flex-col justify-between selection:bg-primary/30 selection:text-white">
        <Component {...pageProps} />
        <GlobalPipelineUI />
      </div>
    </PipelineProvider>
  );
}


