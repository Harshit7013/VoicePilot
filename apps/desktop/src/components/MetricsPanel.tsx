/**
 * MetricsPanel — right sidebar showing reliability metrics and task history.
 */

import type { FC } from 'react';
import type { MetricsSummary, TaskRecord } from '../hooks/useVoicePilot';

interface MetricsPanelProps {
  metrics: MetricsSummary | null;
  tasks: TaskRecord[];
}

function formatDuration(s: number | null | undefined): string {
  if (s === null || s === undefined || isNaN(Number(s))) return '—';
  const n = Number(s);
  return n < 60 ? `${n.toFixed(1)}s` : `${(n / 60).toFixed(1)}m`;
}

function formatTime(ts: number | null | undefined): string {
  if (!ts || isNaN(Number(ts))) return '—';
  return new Date(Number(ts) * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export const MetricsPanel: FC<MetricsPanelProps> = ({ metrics, tasks }) => (
  <aside className="metrics-panel flex-col gap-4" style={{ display: 'flex' }}>
    {/* Reliability Metrics */}
    <div className="card">
      <div className="card-header">
        <span>📊</span>
        <span style={{ fontWeight: 600 }}>Reliability Metrics</span>
      </div>
      <div className="card-body">
        {metrics && typeof metrics.avg_retries === 'number' ? (
          <div className="metrics-grid">
            <div className="metric-card">
              <div className="metric-value">{metrics.task_success_rate ?? 0}%</div>
              <div className="metric-label">Success Rate</div>
            </div>
            <div className="metric-card">
              <div className="metric-value">{metrics.total_tasks ?? 0}</div>
              <div className="metric-label">Total Tasks</div>
            </div>
            <div className="metric-card">
              <div className="metric-value">{formatDuration(metrics.avg_duration_seconds)}</div>
              <div className="metric-label">Avg Duration</div>
            </div>
            <div className="metric-card">
              <div className="metric-value">{Number(metrics.avg_retries ?? 0).toFixed(1)}</div>
              <div className="metric-label">Avg Retries</div>
            </div>
            <div className="metric-card" style={{ gridColumn: '1 / -1' }}>
              <div className="metric-value">{metrics.verified_steps ?? 0}</div>
              <div className="metric-label">Verified Steps</div>
            </div>
          </div>
        ) : (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '2rem 0' }}>
            <div style={{ fontSize: '2rem' }}>📊</div>
            <p style={{ marginTop: '0.5rem', fontSize: '0.8rem' }}>Run tasks to see metrics</p>
          </div>
        )}
      </div>
    </div>

    {/* Task History */}
    <div className="card" style={{ flex: 1 }}>
      <div className="card-header">
        <span>📜</span>
        <span style={{ fontWeight: 600 }}>Task History</span>
        <span style={{ marginLeft: 'auto', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          {tasks.length} tasks
        </span>
      </div>
      <div className="card-body" style={{ overflowY: 'auto', maxHeight: 400 }}>
        {tasks.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', textAlign: 'center', padding: '1.5rem 0' }}>
            No tasks yet
          </p>
        ) : (
          tasks.map(task => (
            <div key={task.id} className="task-item">
              <div className="task-icon">
                {task.status === 'success' ? '✅' : task.status === 'failed' ? '❌' : '⏳'}
              </div>
              <div className="task-info">
                <div className="task-name" title={task.task}>{task.task}</div>
                <div className="task-meta">
                  {formatTime(task.created_at)} · {formatDuration(task.duration_seconds)}
                  {task.total_retries > 0 && ` · ${task.total_retries} retries`}
                </div>
              </div>
              <div className={`task-status-dot ${task.success ? 'success' : 'failed'}`} />
            </div>
          ))
        )}
      </div>
    </div>
  </aside>
);
