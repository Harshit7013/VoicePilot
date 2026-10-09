/**
 * VoicePilot WebSocket & API hook.
 * Maintains a persistent WebSocket connection to the Python agent
 * and provides helper functions for sending commands / confirmations.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

const WS_URL = 'ws://localhost:8765/ws';
const API_URL = 'http://localhost:8765';

export type EventType =
  | 'agent_ready' | 'transcribing' | 'transcribed'
  | 'planning' | 'plan_ready'
  | 'step_start' | 'step_complete' | 'step_failed'
  | 'step_retry' | 'step_blocked' | 'step_recovered'
  | 'task_start' | 'task_complete' | 'task_error'
  | 'confirmation_required' | 'escalation';

export interface AgentEvent {
  type: EventType;
  data: Record<string, unknown>;
  timestamp: number;
}

export interface ConfirmationRequest {
  confirmation_id: string;
  action: string;
  message: string;
}

export interface TaskRecord {
  id: string;
  task: string;
  status: string;
  success: number;
  duration_seconds: number | null;
  total_retries: number;
  error: string | null;
  created_at: number;
}

export interface MetricsSummary {
  total_tasks: number;
  successful_tasks: number;
  task_success_rate: number;
  avg_duration_seconds: number;
  avg_retries: number;
  verified_steps: number;
}

export function useVoicePilot() {
  const ws = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [pendingConfirmation, setPendingConfirmation] = useState<ConfirmationRequest | null>(null);
  const [agentState, setAgentState] = useState<'idle' | 'listening' | 'transcribing' | 'planning' | 'executing' | 'complete' | 'error'>('idle');
  const [currentPlan, setCurrentPlan] = useState<Record<string, unknown> | null>(null);
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [tasks, setTasks] = useState<TaskRecord[]>([]);

  const addEvent = useCallback((event: AgentEvent) => {
    setEvents(prev => [event, ...prev].slice(0, 200));
  }, []);

  const handleMessage = useCallback((raw: MessageEvent) => {
    try {
      const event = JSON.parse(raw.data) as { type: EventType; data: Record<string, unknown> };
      const stamped: AgentEvent = { ...event, timestamp: Date.now() };
      addEvent(stamped);

      switch (event.type) {
        case 'agent_ready':
          setAgentState('idle');
          break;
        case 'transcribing':
          setAgentState('transcribing');
          break;
        case 'planning':
          setAgentState('planning');
          break;
        case 'plan_ready':
          setCurrentPlan(event.data);
          setAgentState('executing');
          break;
        case 'task_complete':
          setAgentState('complete');
          setTimeout(() => setAgentState('idle'), 3000);
          refreshTasks();
          refreshMetrics();
          break;
        case 'task_error':
          setAgentState('error');
          setTimeout(() => setAgentState('idle'), 4000);
          break;
        case 'confirmation_required':
          setPendingConfirmation(event.data as unknown as ConfirmationRequest);
          break;
      }
    } catch {
      // ignore parse errors
    }
  }, [addEvent]);

  useEffect(() => {
    let reconnectTimer: ReturnType<typeof setTimeout>;

    const connect = () => {
      try {
        const socket = new WebSocket(WS_URL);
        ws.current = socket;

        socket.onopen = () => setConnected(true);
        socket.onclose = () => {
          setConnected(false);
          reconnectTimer = setTimeout(connect, 2000);
        };
        socket.onerror = () => { socket.close(); };
        socket.onmessage = handleMessage;
      } catch {
        reconnectTimer = setTimeout(connect, 3000);
      }
    };

    connect();
    return () => {
      clearTimeout(reconnectTimer);
      ws.current?.close();
    };
  }, [handleMessage]);

  const sendCommand = useCallback(async (command: string) => {
    setAgentState('planning');
    try {
      await fetch(`${API_URL}/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command }),
      });
    } catch {
      setAgentState('error');
    }
  }, []);

  const confirm = useCallback(async (confirmation_id: string, approved: boolean) => {
    setPendingConfirmation(null);
    try {
      await fetch(`${API_URL}/confirm/${confirmation_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved }),
      });
    } catch {
      console.error('Confirmation request failed');
    }
  }, []);

  const refreshTasks = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/tasks`);
      const json = await res.json();
      if (json && Array.isArray(json.tasks)) {
        setTasks(json.tasks);
      }
    } catch { /* ignore */ }
  }, []);

  const refreshMetrics = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/metrics`);
      const json = await res.json();
      if (json && !json.error && typeof json.task_success_rate === 'number') {
        setMetrics(json);
      }
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    refreshTasks();
    refreshMetrics();
    const interval = setInterval(() => { refreshTasks(); refreshMetrics(); }, 10000);
    return () => clearInterval(interval);
  }, [refreshTasks, refreshMetrics]);

  return {
    connected,
    agentState,
    events,
    currentPlan,
    pendingConfirmation,
    metrics,
    tasks,
    sendCommand,
    confirm,
  };
}
