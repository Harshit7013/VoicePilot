/**
 * Topbar — brand, connection status, and offline badge.
 */

import type { FC } from 'react';
import { Mic, Lock } from 'lucide-react';

interface TopbarProps {
  connected: boolean;
  agentState: string;
}

export const Topbar: FC<TopbarProps> = ({ connected, agentState }) => {
  const statusDotClass = !connected
    ? 'offline'
    : agentState === 'idle' || agentState === 'complete'
    ? ''
    : agentState === 'error'
    ? 'error'
    : 'thinking';

  const statusText = !connected
    ? 'Connecting...'
    : agentState === 'idle'
    ? 'Ready'
    : agentState === 'listening'
    ? 'Listening'
    : agentState === 'transcribing'
    ? 'Transcribing'
    : agentState === 'planning'
    ? 'Planning'
    : agentState === 'executing'
    ? 'Executing'
    : agentState === 'complete'
    ? 'Complete'
    : agentState === 'error'
    ? 'Error'
    : agentState;

  return (
    <header className="topbar">
      <div className="topbar-brand">
        <Mic className="brand-icon text-primary" size={20} />
        <span className="brand-title">PULSE</span>
        <span className="brand-badge">Offline</span>
      </div>

      <div className="topbar-status">
        <div className={`status-dot ${statusDotClass}`} />
        <span>{statusText}</span>
      </div>

      <div className="flex items-center gap-3">
        <span className="text-xs text-muted">v1.0.0</span>
        <span className="text-xs flex items-center gap-1" title="Privacy-first" style={{ color: 'var(--accent-success)' }}><Lock size={12} /> Local</span>
      </div>
    </header>
  );
};
