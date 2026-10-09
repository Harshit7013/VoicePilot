/**
 * ExecutionTimeline — shows the current task's step-by-step execution.
 */

import type { FC } from 'react';
import type { AgentEvent } from '../hooks/useVoicePilot';

interface ExecutionTimelineProps {
  events: AgentEvent[];
  currentPlan: Record<string, unknown> | null;
}

function getActionIcon(action: string): string {
  const icons: Record<string, string> = {
    open_application: '🚀', click: '👆', type_text: '⌨️', press_key: '⌨️',
    take_screenshot: '📸', scroll: '↕️',
    create_file: '📄', read_file: '📖', write_file: '✏️', delete_file: '🗑️',
    move_file: '📦', copy_file: '📋', create_directory: '📁',
    list_directory: '📋', find_files: '🔍', verify_file: '✅',
    open_browser: '🌐', navigate: '🌍', browser_click: '👆',
    browser_type: '⌨️', browser_search: '🔎', browser_extract: '📤',
    wait: '⏱️', verify_state: '🔍', default: '⚡',
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
        <div className="card-header">
          <span>📋</span>
          <span style={{ fontWeight: 600 }}>Execution Timeline</span>
        </div>
        <div className="card-body" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 200 }}>
          <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🎙️</div>
            <p>Speak or type a command to begin</p>
            <p style={{ fontSize: '0.8rem', marginTop: '0.5rem' }}>VoicePilot will plan, execute, and verify each step</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="card" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="card-header">
        <span>📋</span>
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
                    <div className={`timeline-dot ${status}`}>
                      {status === 'success' ? '✓' : status === 'failed' ? '✕' : getActionIcon(action)}
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
        <div className={`timeline-dot ${status}`}>
          {status === 'success' ? '✓' : status === 'failed' ? '✕' : getActionIcon(action)}
        </div>
        <div className="timeline-line" />
      </div>
      <div className="timeline-content">
        <span className="timeline-action">{action}</span>
      </div>
    </div>
  );
};
