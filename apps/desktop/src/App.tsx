import './index.css';
import { ConfirmationDialog } from './components/ConfirmationDialog';
import { VoicePanel } from './components/VoicePanel';
import { useVoicePilot } from './hooks/useVoicePilot';

function App() {
  const { agentState, pendingConfirmation, sendCommand, confirm } = useVoicePilot();

  return (
    <main className="app-layout">
      <VoicePanel agentState={agentState} onCommand={sendCommand} />

      {pendingConfirmation && (
        <ConfirmationDialog
          request={pendingConfirmation}
          onConfirm={confirm}
        />
      )}
    </main>
  );
}

export default App;
