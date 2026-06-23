import "@/styles/globals.css";
import type { AppProps } from "next/app";
import { PipelineProvider, usePipeline } from "@/lib/PipelineContext";

function GlobalPipelineUI() {
  const { isPipelineRunning, pipelineError, clearError } = usePipeline();

  return (
    <>
      {/* Global Pipeline Running Overlay */}
      {isPipelineRunning && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-md transition-all duration-300">
          <div className="glass-panel-heavy p-8 rounded-2xl shadow-glow flex flex-col items-center gap-5 max-w-sm text-center border border-primary/30 animate-in fade-in zoom-in-95 duration-200">
            <div className="relative w-16 h-16 flex items-center justify-center">
              {/* Outer pulsing ring */}
              <div className="absolute inset-0 rounded-full border-2 border-primary/25 animate-ping"></div>
              {/* Spinning gradient ring */}
              <div className="absolute inset-0 rounded-full border-t-2 border-r-2 border-primary animate-spin"></div>
              <svg className="w-6 h-6 text-primary animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-bold text-text-primary tracking-wide">Executing Pipeline</h3>
              <p className="text-xs text-text-secondary mt-2 leading-relaxed">
                Running 6 risk analysis agents. Fetching news, updating supply chain intelligence. Please wait...
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Floating Error Toast */}
      {pipelineError && (
        <div className="fixed bottom-6 right-6 z-[100] max-w-md w-full glass-panel border border-danger/40 p-4 rounded-xl shadow-glow-danger animate-in slide-in-from-bottom-5 fade-in duration-300">
          <div className="flex items-start gap-3">
            <div className="bg-danger/20 p-2 rounded-lg text-danger shrink-0">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="text-sm font-semibold text-text-primary">Pipeline Execution Failed</h4>
              <p className="text-xs text-text-secondary mt-1 break-words">{pipelineError}</p>
            </div>
            <button 
              onClick={clearError}
              className="text-text-muted hover:text-text-primary transition-colors focus:outline-none"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      )}
    </>
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

