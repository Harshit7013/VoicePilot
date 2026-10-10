/**
 * EventLog — scrollable real-time event stream from the agent.
 */

import { type FC, useEffect, useRef } from 'react';
import type { AgentEvent } from '../hooks/useVoicePilot';
import { Activity } from 'lucide-react';

interface EventLogProps {
  events: AgentEvent[];
}

function getTypeClass(type: string): string {
  if (type.includes('plan')) return 'planning';
  if (type.includes('step_complete') || type.includes('task_complete')) return 'success';
  if (type.includes('fail') || type.includes('error')) return 'error';
  if (type.includes('retry') || type.includes('recover')) return 'recovery';
  return 'executing';
}

function formatEventMessage(event: AgentEvent): string {
  const d = event.data;
  switch (event.type) {
    case 'transcribed':
      return `"${String(d.text || '').slice(0, 80)}"`;
    case 'plan_ready':
      return `${(d.steps as unknown[])?.length || 0} steps · ${String(d.task || '').slice(0, 60)}`;
    case 'step_start':
      return `[${d.step_index}] ${d.action}`;
    case 'step_complete':
      return `[${d.step_index}] ${d.action} ✓${d.verified ? ' verified' : ''}`;
    case 'step_failed':
      return `[${d.step_index}] ${d.action} ✕ ${String(d.error || '').slice(0, 50)}`;
    case 'step_retry':
      return `[${d.step_index}] retry #${d.retry_count} for ${d.action}`;
    case 'step_recovered':
      return `[${d.step_index}] recovered via ${d.stage}`;
    case 'confirmation_required':
      return `confirm: ${d.action} (id: ${String(d.confirmation_id || '').slice(0, 8)})`;
    case 'task_complete': {
      const success = d.success ? 'SUCCESS' : 'FAILED';
      return `${success} · ${String(d.task || '').slice(0, 60)}`;
    }
    case 'escalation':
      return `ESCALATED: ${d.action} — ${String(d.error || '').slice(0, 60)}`;
    default:
      return JSON.stringify(d).slice(0, 80);
  }
}

export const EventLog: FC<EventLogProps> = ({ events }) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events.length]);

  return (
    <div className="card">
      <div className="card-header flex items-center gap-2">
        <Activity size={18} className="text-primary" />
        <span style={{ fontWeight: 600 }}>Live Event Log</span>
        <span style={{ marginLeft: 'auto', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
          {events.length} events
        </span>
      </div>
      <div className="card-body" style={{ padding: '0.75rem' }}>
        <div className="event-log" role="log" aria-live="polite" aria-label="Agent event log">
          {events.length === 0 && (
            <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '1rem' }}>
              Waiting for events…
            </div>
          )}
          {[...events].reverse().map((e, i) => (
            <div key={i} className="log-line">
              <span className="log-time">
                {new Date(e.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </span>
              <span className={`log-type ${getTypeClass(e.type)}`}>{e.type}</span>
              <span className="log-msg">{formatEventMessage(e)}</span>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      </div>
    </div>
  );
};
