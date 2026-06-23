import Link from 'next/link';
import { useRouter } from 'next/router';
import { usePipeline } from '../lib/PipelineContext';

export default function Navbar() {
  const { isPipelineRunning, runPipeline } = usePipeline();
  const router = useRouter();

  const handleRunPipeline = async () => {
    await runPipeline();
  };

  const isActive = (path: string) => router.pathname === path;

  return (
    <nav className="glass-panel sticky top-0 z-50 transition-all duration-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          <div className="flex items-center gap-10">
            <Link href="/" className="flex items-center gap-2 group">
              <div className="relative w-8 h-8 flex items-center justify-center rounded-lg bg-primary/10 border border-primary/30 group-hover:border-primary/60 transition-colors duration-300">
                <span className="text-primary text-lg font-bold group-hover:scale-110 transition-transform duration-300">⚡</span>
                <span className="absolute inset-0 rounded-lg bg-primary/20 animate-pulse-glow"></span>
              </div>
              <span className="text-xl font-extrabold tracking-wider bg-clip-text text-transparent bg-gradient-to-r from-primary to-accent-cyan">
                RISK<span className="text-text-primary">RADAR</span>
              </span>
            </Link>
            
            <div className="hidden md:flex items-center space-x-2">
              <Link 
                href="/" 
                className={`px-4 py-1.5 rounded-lg text-sm font-semibold transition-all duration-300 ${
                  isActive('/') 
                    ? 'bg-primary/10 text-primary border border-primary/20 shadow-glow' 
                    : 'text-text-secondary hover:text-text-primary hover:bg-white/5 border border-transparent'
                }`}
              >
                Dashboard
              </Link>
              <Link 
                href="/queue" 
                className={`px-4 py-1.5 rounded-lg text-sm font-semibold transition-all duration-300 ${
                  isActive('/queue') 
                    ? 'bg-primary/10 text-primary border border-primary/20 shadow-glow' 
                    : 'text-text-secondary hover:text-text-primary hover:bg-white/5 border border-transparent'
                }`}
              >
                Approval Queue
              </Link>
            </div>
          </div>
          
          <div className="flex items-center">
            <button
              onClick={handleRunPipeline}
              disabled={isPipelineRunning}
              className="relative overflow-hidden bg-primary hover:bg-primary-hover text-white font-semibold px-5 py-2 rounded-xl text-sm transition-all duration-300 shadow-glow disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 border border-primary/40 active:scale-95"
            >
              {isPipelineRunning ? (
                <>
                  <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span>Running...</span>
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  <span>Trigger Pipeline</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}

