/**
 * VoicePanel — microphone button, waveform, and text command input.
 */

import { type FC, type KeyboardEvent, useRef, useState } from 'react';
import { Mic, Square, Loader2, Send, Camera, MessageSquare } from 'lucide-react';

interface VoicePanelProps {
  agentState: string;
  onCommand: (command: string) => void;
}

export const VoicePanel: FC<VoicePanelProps> = ({ agentState, onCommand }) => {
  const [text, setText] = useState('');
  const [listening, setListening] = useState(false);
  const [mode, setMode] = useState<'camera' | 'voice' | 'text'>('voice');
  const recognitionRef = useRef<any>(null);

  // Initialize SpeechRecognition
  if (typeof window !== 'undefined' && !recognitionRef.current) {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = 'en-US';
      recognitionRef.current = recognition;
    }
  }

  const isbusy = agentState !== 'idle' && agentState !== 'complete' && agentState !== 'error';

  const handleVoiceToggle = () => {
    if (listening) {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      setListening(false);
    } else {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.onresult = (event: any) => {
            const transcript = Array.from(event.results)
              .map((result: any) => result[0].transcript)
              .join('');
            
            setText(transcript);

            // Stop listening when final, but DO NOT auto-submit so the user can edit.
            if (event.results[0].isFinal) {
              setListening(false);
            }
          };

          recognitionRef.current.onerror = (event: any) => {
            console.error('Speech recognition error:', event.error);
            setListening(false);
            if (event.error !== 'no-speech') {
              alert(`Speech recognition error: ${event.error}`);
            }
          };

          recognitionRef.current.onend = () => {
            setListening(false);
          };

          recognitionRef.current.start();
          setListening(true);
        } catch (e: any) {
          alert(`Speech recognition failed to start: ${e.message}`);
        }
      } else {
        alert("Speech recognition is not supported in this browser. Please use Chrome or Edge.");
      }
    }
  };

  const handleTextSubmit = () => {
    const trimmed = text.trim();
    if (trimmed && !isbusy) {
      onCommand(trimmed);
      setText('');
      setMode('text'); // Switch back to text or remain in current mode
    }
  };

  const handleCameraSubmit = () => {
    onCommand("take a screenshot of the screen");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleTextSubmit();
  };

  return (
    <div className="card" style={{ overflow: 'hidden', padding: 0 }}>
      {/* 3 Main Mode Options */}
      <div className="flex border-b border-white/10" style={{ backgroundColor: 'rgba(0,0,0,0.2)' }}>
        <button
          className={`flex-1 flex flex-col items-center gap-2 py-4 transition-all ${mode === 'camera' ? 'bg-primary/20 text-primary border-b-2 border-primary' : 'text-gray-400 hover:bg-white/5 hover:text-white'}`}
          onClick={() => setMode('camera')}
        >
          <Camera size={24} />
          <span className="text-xs font-semibold uppercase tracking-wider">Screenshot</span>
        </button>
        <button
          className={`flex-1 flex flex-col items-center gap-2 py-4 transition-all ${mode === 'voice' ? 'bg-primary/20 text-primary border-b-2 border-primary' : 'text-gray-400 hover:bg-white/5 hover:text-white'}`}
          onClick={() => setMode('voice')}
        >
          <Mic size={24} />
          <span className="text-xs font-semibold uppercase tracking-wider">Voice</span>
        </button>
        <button
          className={`flex-1 flex flex-col items-center gap-2 py-4 transition-all ${mode === 'text' ? 'bg-primary/20 text-primary border-b-2 border-primary' : 'text-gray-400 hover:bg-white/5 hover:text-white'}`}
          onClick={() => setMode('text')}
        >
          <MessageSquare size={24} />
          <span className="text-xs font-semibold uppercase tracking-wider">Text</span>
        </button>
      </div>

      <div className="p-5 flex flex-col gap-4 min-h-[220px] justify-center relative">
        {/* Agent Status Overlay */}
        {isbusy && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-black/60 backdrop-blur-sm">
            <Loader2 size={32} className="animate-spin text-primary mb-3" />
            <span className="text-sm font-medium text-white/90 uppercase tracking-widest">
              {agentState === 'planning' ? 'Planning...' : agentState === 'executing' ? 'Executing Task...' : 'Working...'}
            </span>
          </div>
        )}

        {/* Camera Mode */}
        {mode === 'camera' && (
          <div className="flex flex-col items-center justify-center gap-4 animate-in fade-in zoom-in duration-300">
            <div className="w-16 h-16 rounded-full bg-primary/20 flex items-center justify-center text-primary mb-2 shadow-[0_0_15px_rgba(var(--primary-rgb),0.3)]">
              <Camera size={32} />
            </div>
            <p className="text-sm text-center text-gray-300 mb-2">
              Take a screenshot of your screen to analyze or work on it.
            </p>
            <button
              className="btn btn-primary px-8 py-3 rounded-full text-sm font-bold shadow-lg"
              onClick={handleCameraSubmit}
              disabled={isbusy}
            >
              Capture Screen
            </button>
          </div>
        )}

        {/* Voice Mode */}
        {mode === 'voice' && (
          <div className="flex flex-col items-center gap-4 animate-in fade-in zoom-in duration-300 w-full">
            <button
              className={`w-20 h-20 rounded-full flex items-center justify-center transition-all duration-300 shadow-xl ${listening ? 'bg-danger text-white scale-110 shadow-[0_0_30px_rgba(255,50,50,0.6)] animate-pulse' : 'bg-primary text-black hover:scale-105'}`}
              onClick={handleVoiceToggle}
              disabled={isbusy}
            >
              {listening ? <Square size={28} /> : <Mic size={32} />}
            </button>
            <p className="text-xs text-gray-400 font-medium">
              {listening ? "Recording... Click to stop." : "Click to speak"}
            </p>
          </div>
        )}

        {/* Text/Edit Mode (Shown in both Voice and Text modes so they can edit Voice) */}
        {(mode === 'text' || mode === 'voice') && (
          <div className="mt-auto animate-in slide-in-from-bottom-4 duration-300">
            {mode === 'voice' && text && (
              <p className="text-xs text-primary mb-2 font-medium px-1">Review & edit your command:</p>
            )}
            <div className="relative flex items-center">
              <input
                type="text"
                className="w-full bg-black/40 border border-white/10 rounded-2xl py-3 pl-4 pr-12 text-sm text-white focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all placeholder:text-gray-500"
                placeholder={mode === 'voice' ? "Or type a command here..." : "Type your command..."}
                value={text}
                onChange={e => setText(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isbusy}
              />
              <button
                className="absolute right-2 p-2 rounded-xl bg-primary text-black hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                onClick={handleTextSubmit}
                disabled={isbusy || !text.trim()}
              >
                <Send size={16} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
