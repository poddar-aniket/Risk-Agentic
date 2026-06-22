import Link from 'next/link';
import { triggerPipeline } from '../lib/api';
import { useState } from 'react';

export default function Navbar() {
  const [isRunning, setIsRunning] = useState(false);

  const handleRunPipeline = async () => {
    setIsRunning(true);
    try {
      await triggerPipeline();
      alert('Pipeline triggered successfully');
    } catch (error) {
      alert('Failed to trigger pipeline');
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <nav className="bg-surface border-b border-border sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          <div className="flex items-center gap-8">
            <Link href="/" className="flex items-center">
              <span className="text-xl font-bold text-primary tracking-tight">RiskRadar</span>
            </Link>
            <div className="hidden md:flex items-center space-x-4">
              <Link href="/" className="text-text-secondary hover:text-text-primary px-3 py-2 rounded-md text-sm font-medium transition-colors">
                Dashboard
              </Link>
              <Link href="/queue" className="text-text-secondary hover:text-text-primary px-3 py-2 rounded-md text-sm font-medium transition-colors">
                Queue
              </Link>
            </div>
          </div>
          <div className="flex items-center">
            <button
              onClick={handleRunPipeline}
              disabled={isRunning}
              className="bg-primary hover:bg-amber-500 text-background px-4 py-2 rounded-md text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isRunning ? 'Running...' : 'Trigger Pipeline'}
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}
