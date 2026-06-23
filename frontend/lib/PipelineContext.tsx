import React, { createContext, useContext, useState } from 'react';
import { triggerPipeline } from './api';

interface PipelineContextType {
  isPipelineRunning: boolean;
  pipelineError: string | null;
  runPipeline: () => Promise<boolean>;
  clearError: () => void;
}

const PipelineContext = createContext<PipelineContextType | undefined>(undefined);

export const PipelineProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isPipelineRunning, setIsPipelineRunning] = useState(false);
  const [pipelineError, setPipelineError] = useState<string | null>(null);

  const runPipeline = async (): Promise<boolean> => {
    setIsPipelineRunning(true);
    setPipelineError(null);
    try {
      const response = await triggerPipeline();
      if (!response.ok) {
        let errMessage = 'Pipeline execution failed on the server.';
        try {
          const errData = await response.json();
          if (errData) {
            errMessage = errData.detail || errData.error || errMessage;
          }
        } catch (_) {}
        throw new Error(errMessage);
      }
      return true;
    } catch (error: any) {
      console.error('Pipeline error:', error);
      setPipelineError(error?.message || 'Failed to connect to the backend server. Make sure the server is running.');
      return false;
    } finally {
      setIsPipelineRunning(false);
    }
  };

  const clearError = () => {
    setPipelineError(null);
  };

  return (
    <PipelineContext.Provider
      value={{
        isPipelineRunning,
        pipelineError,
        runPipeline,
        clearError,
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
