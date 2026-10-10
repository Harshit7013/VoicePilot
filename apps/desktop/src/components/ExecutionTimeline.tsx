/**
 * ExecutionTimeline — shows the current task's step-by-step execution.
 */

import type { FC, ReactNode } from 'react';
import type { AgentEvent } from '../hooks/useVoicePilot';
import { ListTodo, Mic, Terminal, MousePointer2, Keyboard, FileText, Trash, Move, Copy, Folder, Search, CheckSquare, Globe, Eye, Zap, FileCode2, Clock, Image, FileSearch, Navigation, Check, X } from 'lucide-react';

interface ExecutionTimelineProps {
  events: AgentEvent[];
  currentPlan: Record<string, unknown> | null;
}

function getActionIcon(action: string): ReactNode {
  const icons: Record<string, ReactNode> = {
    open_application: <Terminal size={14} />, click: <MousePointer2 size={14} />, type_text: <Keyboard size={14} />, press_key: <Keyboard size={14} />,
    take_screenshot: <Image size={14} />, scroll: <Navigation size={14} />,
    create_file: <FileText size={14} />, read_file: <FileCode2 size={14} />, write_file: <FileText size={14} />, delete_file: <Trash size={14} />,
    move_file: <Move size={14} />, copy_file: <Copy size={14} />, create_directory: <Folder size={14} />,
    list_directory: <FileSearch size={14} />, find_files: <Search size={14} />, verify_file: <CheckSquare size={14} />,
    open_browser: <Globe size={14} />, navigate: <Globe size={14} />, browser_click: <MousePointer2 size={14} />,
    browser_type: <Keyboard size={14} />, browser_search: <Search size={14} />, browser_extract: <Eye size={14} />,
    wait: <Clock size={14} />, verify_state: <Search size={14} />, default: <Zap size={14} />,
  };
  return icons[action] || icons.default;
}

export const ExecutionTimeline: FC<ExecutionTimelineProps> = ({ events, currentPlan }) => {
  // Filter events relevant to the current task
  const taskEvents = events.filter(e =>
    ['step_start', 'step_complete', 'step_failed', 'step_retry', 'step_recovered', 'step_blocked'].includes(e.type)
  );

  // Build steps from plan + overlay results
  const steps = (currentPlan?.steps as Array<Record<string, unknown>> | null) || [];
  const resultsMap = new Map<number, AgentEvent>();
  taskEvents.forEach(e => {
    const idx = e.data.step_index as number;
    if (idx !== undefined) resultsMap.set(idx, e);
  });

  if (!currentPlan && taskEvents.length === 0) {
    return (
      <div className="card" style={{ height: '100%' }}>
        <div className="card-header flex items-center gap-2">
          <ListTodo size={18} className="text-primary" />
          <span style={{ fontWeight: 600 }}>Execution Timeline</span>
        </div>
        <div className="card-body" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 200 }}>
          <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '1rem' }}><Mic size={48} className="text-muted opacity-50" /></div>
            <p>Speak or type a command to begin</p>
            <p style={{ fontSize: '0.8rem', marginTop: '0.5rem' }}>PULSE will plan, execute, and verify each step</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="card" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="card-header flex items-center gap-2">
        <ListTodo size={18} className="text-primary" />
        <span style={{ fontWeight: 600 }}>Execution Timeline</span>
        {Boolean(currentPlan?.task) && (
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginLeft: 'auto' }} className="truncate">
            {String(currentPlan?.task)}
          </span>
        )}
      </div>

      <div className="card-body" style={{ flex: 1, overflowY: 'auto' }}>
        {steps.length === 0 && taskEvents.length > 0 && (
          <div className="timeline">
            {taskEvents.map((e, idx) => (
              <TimelineRow key={idx} event={e} stepIndex={idx} />
            ))}
          </div>
        )}

        {steps.length > 0 && (
          <div className="timeline">
            {steps.map((step, i) => {
              const result = resultsMap.get(i);
              const status = !result ? 'pending'
                : result.type === 'step_complete' ? 'success'
                : result.type === 'step_failed' ? 'failed'
                : result.type === 'step_retry' ? 'running'
                : result.type === 'step_start' ? 'running'
                : 'pending';

              const action = String(step.action || 'action');
              const risk = String(step.risk || 'low');

              return (
                <div key={i} className="timeline-item">
                  <div className="timeline-dot-wrap">
                    <div className={`timeline-dot ${status} flex items-center justify-center`}>
                      {status === 'success' ? <Check size={12} /> : status === 'failed' ? <X size={12} /> : getActionIcon(action)}
                    </div>
                    <div className="timeline-line" />
                  </div>
                  <div className="timeline-content">
                    <div className="flex items-center gap-2" style={{ flexWrap: 'wrap', marginBottom: 4 }}>
                      <span className="timeline-action">{action}</span>
                      <span className={`risk-pill risk-${risk}`}>{risk}</span>
                      {result?.type === 'step_complete' && (
                        <span className="timeline-badge badge-verified">verified</span>
                      )}
                      {result?.type === 'step_retry' && (
                        <span className="timeline-badge badge-retried">
                          retry {String(result.data.retry_count || '')}
                        </span>
                      )}
                    </div>
                    {Boolean(result?.data?.output) && (
                      <div className="timeline-output">
                        {Array.isArray(result?.data?.output)
                          ? `${(result.data.output as string[]).length} items found`
                          : String(result?.data?.output).slice(0, 120)}
                      </div>
                    )}
                    {Boolean(result?.data?.error) && (
                      <div className="timeline-error">⚠ {String(result?.data?.error).slice(0, 100)}</div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

const TimelineRow: FC<{ event: AgentEvent; stepIndex: number }> = ({ event }) => {
  const action = String(event.data.action || 'action');
  const status = event.type === 'step_complete' ? 'success'
    : event.type === 'step_failed' ? 'failed'
    : 'running';

  return (
    <div className="timeline-item">
      <div className="timeline-dot-wrap">
        <div className={`timeline-dot ${status} flex items-center justify-center`}>
          {status === 'success' ? <Check size={12} /> : status === 'failed' ? <X size={12} /> : getActionIcon(action)}
        </div>
        <div className="timeline-line" />
      </div>
      <div className="timeline-content">
        <span className="timeline-action">{action}</span>
      </div>
    </div>
  );
};
