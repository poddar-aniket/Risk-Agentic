import React, { createContext, useContext, useState } from 'react';

interface PipelineContextType {
  isPipelineRunning: boolean;
  pipelineError: string | null;
  activeNode: string | null;
  pipelineLogs: string[];
  runPipeline: () => Promise<boolean>;
  clearError: () => void;
  closeVisualizer: () => void;
}

const PipelineContext = createContext<PipelineContextType | undefined>(undefined);

export const PipelineProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isPipelineRunning, setIsPipelineRunning] = useState(false);
  const [pipelineError, setPipelineError] = useState<string | null>(null);
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [pipelineLogs, setPipelineLogs] = useState<string[]>([]);

  const runPipeline = async (): Promise<boolean> => {
    setIsPipelineRunning(true);
    setPipelineError(null);
    setActiveNode(null);
    setPipelineLogs(["[System] Starting supply chain threat monitor pipeline..."]);

    try {
      const response = await fetch('/api/pipeline/run', { method: 'POST' });
      if (!response.ok) {
        throw new Error("Server rejected pipeline execution request.");
      }

      if (!response.body) {
        throw new Error("Response body is not readable.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const cleanLine = line.replace(/^data:\s*/, "").trim();
          if (!cleanLine) continue;

          try {
            const data = JSON.parse(cleanLine);
            
            if (data.message) {
              const prefix = data.status === 'progress' ? `[${data.node}]` : '[System]';
              setPipelineLogs(prev => [...prev, `${prefix} ${data.message}`]);
            }

            if (data.status === "ingesting") {
              setActiveNode("ingesting");
            } else if (data.status === "start") {
              setActiveNode("start");
            } else if (data.status === "progress") {
              setActiveNode(data.node);
            } else if (data.status === "skipped") {
              throw new Error(data.message || "No new articles found.");
            } else if (data.status === "error") {
              throw new Error(data.message || "Pipeline execution encountered an error.");
            } else if (data.status === "completed") {
              setActiveNode("completed");
            }
          } catch (e: any) {
            // Propagate known error messages from stream
            if (e.message && (
              e.message.includes("No new") || 
              e.message.includes("failed") || 
              e.message.includes("error") || 
              e.message.includes("skipped") ||
              e.message.includes("encountered")
            )) {
              throw e;
            }
            console.error("SSE parse error:", e);
          }
        }
      }
      return true;
    } catch (error: any) {
      console.error('Pipeline stream error:', error);
      setPipelineError(error?.message || 'Failed to complete pipeline execution.');
      return false;
    }
  };

  const clearError = () => {
    setPipelineError(null);
  };

  const closeVisualizer = () => {
    setIsPipelineRunning(false);
    setActiveNode(null);
    setPipelineError(null);
    setPipelineLogs([]);
  };

  return (
    <PipelineContext.Provider
      value={{
        isPipelineRunning,
        pipelineError,
        activeNode,
        pipelineLogs,
        runPipeline,
        clearError,
        closeVisualizer,
      }}
    >
      {children}
    </PipelineContext.Provider>
  );
};

export const usePipeline = () => {
  const context = useContext(PipelineContext);
  if (context === undefined) {
    throw new Error('usePipeline must be used within a PipelineProvider');
  }
  return context;
};

