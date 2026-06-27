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
    <nav className="bg-zinc-700 shadow-sm border border-zinc-500 rounded-2xl sticky top-0 z-50 transition-all duration-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          <div className="flex items-center gap-10">
            <Link href="/" className="flex items-center gap-2 group">
              <div className="relative w-8 h-8 flex items-center justify-center rounded-lg bg-emerald-500/10 border border-emerald-600/30 group-hover:border-emerald-600/60 transition-colors duration-300">
                <svg className="w-5 h-5 text-emerald-400 group-hover:scale-110 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                <span className="absolute inset-0 rounded-lg bg-emerald-500/20 animate-pulse-glow"></span>
              </div>
              <span className="text-xl font-extrabold tracking-wider bg-clip-text text-transparent bg-gradient-to-r from-primary to-emerald-400">
                RISK<span className="text-zinc-50">RADAR</span>
              </span>
            </Link>
            
            <div className="hidden md:flex items-center space-x-2">
              <Link 
                href="/" 
                className={`px-4 py-1.5 rounded-lg text-sm font-semibold transition-all duration-300 ${
                  isActive('/') 
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-600/20 shadow-glow' 
                    : 'text-zinc-200 hover:text-zinc-50 hover:bg-zinc-800 border border-transparent'
                }`}
              >
                Dashboard
              </Link>
              <Link 
                href="/queue" 
                className={`px-4 py-1.5 rounded-lg text-sm font-semibold transition-all duration-300 ${
                  isActive('/queue') 
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-600/20 shadow-glow' 
                    : 'text-zinc-200 hover:text-zinc-50 hover:bg-zinc-800 border border-transparent'
                }`}
              >
                Approval Queue
              </Link>
              <Link 
                href="/database" 
                className={`px-4 py-1.5 rounded-lg text-sm font-semibold transition-all duration-300 ${
                  isActive('/database') 
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-600/20 shadow-glow' 
                    : 'text-zinc-200 hover:text-zinc-50 hover:bg-zinc-800 border border-transparent'
                }`}
              >
                Database
              </Link>
            </div>
          </div>
          
          <div className="flex items-center">
            <button
              onClick={handleRunPipeline}
              disabled={isPipelineRunning}
              className="relative overflow-hidden bg-emerald-500 hover:bg-emerald-500-hover text-zinc-50 font-semibold px-5 py-2 rounded-xl text-sm transition-all duration-300 shadow-glow disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 border border-emerald-600/40 active:scale-95"
            >
              {isPipelineRunning ? (
                <>
                  <svg className="animate-spin h-4 w-4 text-zinc-50" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
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

