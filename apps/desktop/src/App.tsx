/**
 * VoicePilot — Main Application Entry Point
 * Wires together all UI components with the agent hook.
 */

import './index.css';
import { ConfirmationDialog } from './components/ConfirmationDialog';
import { EventLog } from './components/EventLog';
import { ExecutionTimeline } from './components/ExecutionTimeline';
import { MetricsPanel } from './components/MetricsPanel';
import { Topbar } from './components/Topbar';
import { VoicePanel } from './components/VoicePanel';
import { useVoicePilot } from './hooks/useVoicePilot';

function App() {
  const {
    connected,
    agentState,
    events,
    currentPlan,
    pendingConfirmation,
    metrics,
    tasks,
    sendCommand,
    confirm,
  } = useVoicePilot();

  return (
    <div className="app-layout">
      <Topbar connected={connected} agentState={agentState} />

      <main className="main-content">
        {/* Left sidebar — voice input */}
        <aside className="sidebar flex-col gap-4" style={{ display: 'flex' }}>
          <VoicePanel agentState={agentState} onCommand={sendCommand} />
          <EventLog events={events} />
        </aside>

        {/* Center — execution timeline */}
        <section style={{ minHeight: 0 }}>
          <ExecutionTimeline events={events} currentPlan={currentPlan} />
        </section>

        {/* Right — metrics and history */}
        <MetricsPanel metrics={metrics} tasks={tasks} />
      </main>

      {/* Confirmation modal overlay */}
      {pendingConfirmation && (
        <ConfirmationDialog
          request={pendingConfirmation}
          onConfirm={confirm}
        />
      )}
    </div>
  );
}

export default App;
