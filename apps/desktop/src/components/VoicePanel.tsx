/**
 * VoicePanel — microphone button, waveform, and text command input.
 */

import { type FC, type KeyboardEvent, useRef, useState } from 'react';

interface VoicePanelProps {
  agentState: string;
  onCommand: (command: string) => void;
}

// Microphone recording using MediaRecorder
async function startRecording(): Promise<{ stop: () => Promise<Blob> }> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const recorder = new MediaRecorder(stream);
  const chunks: BlobPart[] = [];

  return new Promise(resolve => {
    recorder.ondataavailable = e => chunks.push(e.data);
    recorder.start();

    resolve({
      stop: () => new Promise(res => {
        recorder.onstop = () => {
          stream.getTracks().forEach(t => t.stop());
          res(new Blob(chunks, { type: 'audio/webm' }));
        };
        recorder.stop();
      }),
    });
  });
}

async function blobToBase64(blob: Blob): Promise<string> {
  return new Promise(resolve => {
    const reader = new FileReader();
    reader.onloadend = () => resolve((reader.result as string).split(',')[1]);
    reader.readAsDataURL(blob);
  });
}

export const VoicePanel: FC<VoicePanelProps> = ({ agentState, onCommand }) => {
  const [text, setText] = useState('');
  const [listening, setListening] = useState(false);
  const recorderRef = useRef<{ stop: () => Promise<Blob> } | null>(null);

  const isbusy = agentState !== 'idle' && agentState !== 'complete' && agentState !== 'error';

  const handleVoiceToggle = async () => {
    if (listening) {
      // Stop recording and send audio
      if (recorderRef.current) {
        const blob = await recorderRef.current.stop();
        recorderRef.current = null;
        setListening(false);

        const base64 = await blobToBase64(blob);
        try {
          const res = await fetch('http://localhost:8765/audio', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ audio_base64: base64, sample_rate: 48000 }),
          });
          const result = await res.json();
          console.log('Audio result:', result);
        } catch {
          // Fall back to simulated command for demo
          onCommand('Create a folder named Hackathon Demo with a text file saying VoicePilot works offline.');
        }
      }
    } else {
      // Start recording
      try {
        recorderRef.current = await startRecording();
        setListening(true);
      } catch {
        // Mic not available — use demo command
        onCommand('Create a folder named Hackathon Demo with a text file saying VoicePilot works offline.');
      }
    }
  };

  const handleTextSubmit = () => {
    const trimmed = text.trim();
    if (trimmed && !isbusy) {
      onCommand(trimmed);
      setText('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleTextSubmit();
  };

  const voiceBtnClass = listening ? 'listening' : isbusy ? 'processing' : '';
  const voiceBtnIcon = listening ? '⏹️' : isbusy ? '⏳' : '🎙️';
  const statusText = listening
    ? 'Recording… click to stop'
    : agentState === 'transcribing'
    ? 'Transcribing audio…'
    : agentState === 'planning'
    ? 'Planning actions…'
    : agentState === 'executing'
    ? 'Executing task…'
    : agentState === 'complete'
    ? '✅ Task complete!'
    : agentState === 'error'
    ? '❌ Error occurred'
    : 'Click to speak or type a command';

  return (
    <div className="card" style={{ overflow: 'hidden' }}>
      <div className="card-header">
        <span>🎙️</span>
        <span style={{ fontWeight: 600 }}>Voice Command</span>
      </div>

      {/* Stage progress bar */}
      <div className="stage-bar">
        {['Listen', 'Transcribe', 'Plan', 'Execute', 'Verify'].map((stage, i) => {
          const stages = ['listening', 'transcribing', 'planning', 'executing', 'complete'];
          const currentIdx = stages.indexOf(agentState);
          const cls = i < currentIdx ? 'done' : i === currentIdx ? 'active' : '';
          return <div key={stage} className={`stage-step ${cls}`} title={stage} />;
        })}
      </div>

      <div className="voice-section">
        <button
          id="voice-btn"
          className={`voice-btn ${voiceBtnClass}`}
          onClick={handleVoiceToggle}
          disabled={isbusy && !listening}
          title={listening ? 'Stop recording' : 'Start recording'}
          aria-label={listening ? 'Stop recording' : 'Start voice command'}
        >
          <span className="voice-btn-icon">{voiceBtnIcon}</span>
        </button>

        <div className="voice-waveform" aria-hidden="true">
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="wave-bar" />
          ))}
        </div>

        <p className="voice-status-text">{statusText}</p>
      </div>

      {/* Text fallback */}
      <div className="command-input-wrap">
        <input
          id="text-command-input"
          type="text"
          className="command-input"
          placeholder="Or type a command and press Enter…"
          value={text}
          onChange={e => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isbusy}
          aria-label="Text command input"
        />
        <button
          id="send-command-btn"
          className="btn btn-primary"
          onClick={handleTextSubmit}
          disabled={isbusy || !text.trim()}
        >
          ▶
        </button>
      </div>

      {/* Demo quick commands */}
      <div style={{ padding: '0 1.5rem 1.25rem' }}>
        <p className="section-title" style={{ marginBottom: '0.5rem' }}>Quick demos</p>
        <div className="flex" style={{ flexWrap: 'wrap', gap: '0.4rem' }}>
          {[
            'Create a folder named Hackathon Demo with a text file saying VoicePilot works offline.',
            'Open Calculator and compute 125 × 48',
            'Find PDF files in Downloads and move to Desktop',
            'Search Google for VoicePilot offline AI agent',
          ].map((cmd, i) => (
            <button
              key={i}
              className="btn btn-ghost"
              style={{ fontSize: '0.72rem', padding: '3px 10px' }}
              onClick={() => onCommand(cmd)}
              disabled={isbusy}
            >
              {cmd.slice(0, 28)}…
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
