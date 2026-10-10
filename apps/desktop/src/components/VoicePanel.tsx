import { type FC, type FormEvent, useEffect, useRef, useState } from 'react';
import { Camera, Mic, Send, Square, Type } from 'lucide-react';

interface VoicePanelProps {
  agentState: string;
  onCommand: (command: string) => void;
}

type Mode = 'camera' | 'voice' | 'text';

interface SpeechRecognitionLike {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
}

interface SpeechRecognitionEventLike {
  results: ArrayLike<{ isFinal: boolean; [index: number]: { transcript: string } }>;
}

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

const stateLabel: Record<string, string> = {
  planning: 'Preparing your request…',
  transcribing: 'Transcribing…',
  executing: 'Working on it…',
  complete: 'Done',
  error: 'Something went wrong',
};

export const VoicePanel: FC<VoicePanelProps> = ({ agentState, onCommand }) => {
  const [mode, setMode] = useState<Mode>('voice');
  const [command, setCommand] = useState('');
  const [listening, setListening] = useState(false);
  const [notice, setNotice] = useState('Tap the microphone and say what you need.');
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const isBusy = !['idle', 'complete', 'error'].includes(agentState);

  useEffect(() => {
    const recognitionConstructor = (
      window as Window & {
        SpeechRecognition?: SpeechRecognitionConstructor;
        webkitSpeechRecognition?: SpeechRecognitionConstructor;
      }
    ).SpeechRecognition || (
      window as Window & { webkitSpeechRecognition?: SpeechRecognitionConstructor }
    ).webkitSpeechRecognition;

    if (!recognitionConstructor) return;

    const recognition = new recognitionConstructor();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'en-US';
    recognitionRef.current = recognition;

    recognition.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map((result) => result[0].transcript)
        .join('')
        .trim();
      const isFinal = Array.from(event.results).some((result) => result.isFinal);

      setCommand(transcript);
      setNotice(transcript ? `I heard: “${transcript}”` : 'Listening…');

      if (isFinal && transcript) {
        setListening(false);
        onCommand(transcript);
      }
    };

    recognition.onerror = ({ error }) => {
      setListening(false);
      setNotice(
        error === 'not-allowed'
          ? 'Microphone access is blocked. Allow it in your browser settings and try again.'
          : 'I could not hear that. Please try again.',
      );
    };

    recognition.onend = () => setListening(false);

    return () => {
      try {
        recognition.stop();
      } catch {
        // Recognition was never started or has already stopped.
      }
      recognitionRef.current = null;
    };
  }, [onCommand]);

  useEffect(() => {
    if (mode === 'text') inputRef.current?.focus();
  }, [mode]);

  const selectCamera = () => {
    setMode('camera');
    if (isBusy) return;

    setNotice('Capturing your screen…');
    onCommand('take a screenshot of the screen');
  };

  const toggleListening = () => {
    setMode('voice');
    if (isBusy) return;

    const recognition = recognitionRef.current;
    if (!recognition) {
      setNotice('Speech recognition is unavailable here. You can use the text option instead.');
      return;
    }

    if (listening) {
      recognition.stop();
      setListening(false);
      setNotice('Listening stopped.');
      return;
    }

    try {
      setCommand('');
      setNotice('Listening…');
      recognition.start();
      setListening(true);
    } catch {
      setNotice('The microphone is already starting. Please speak when it is ready.');
    }
  };

  const selectText = () => {
    setMode('text');
    setNotice('Type a request and press Enter or Send.');
  };

  const submitText = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = command.trim();
    if (!trimmed || isBusy) return;

    onCommand(trimmed);
    setCommand('');
    setNotice('Preparing your request…');
  };

  const currentNotice = isBusy ? stateLabel[agentState] ?? 'Working…' : notice;

  return (
    <section className="command-launcher" aria-label="VoicePilot command options">
      <div className="launcher-copy">
        <p className="product-name">VoicePilot</p>
        <h1>What would you like to do?</h1>
        <p className="launcher-subtitle">Choose a way to start a command.</p>
      </div>

      <div className="command-options" aria-label="Command input options">
        <button
          className={`command-option ${mode === 'camera' ? 'is-selected' : ''}`}
          onClick={selectCamera}
          disabled={isBusy}
          type="button"
          aria-label="Capture screen"
        >
          <span className="option-icon"><Camera aria-hidden="true" size={27} strokeWidth={1.8} /></span>
          <span>Camera</span>
        </button>

        <button
          className={`command-option command-option--mic ${mode === 'voice' ? 'is-selected' : ''} ${listening ? 'is-listening' : ''}`}
          onClick={toggleListening}
          disabled={isBusy}
          type="button"
          aria-label={listening ? 'Stop listening' : 'Start listening'}
          aria-pressed={listening}
        >
          <span className="option-icon">
            {listening ? <Square aria-hidden="true" size={22} fill="currentColor" /> : <Mic aria-hidden="true" size={29} strokeWidth={1.8} />}
          </span>
          <span>{listening ? 'Listening' : 'Mic'}</span>
        </button>

        <button
          className={`command-option ${mode === 'text' ? 'is-selected' : ''}`}
          onClick={selectText}
          disabled={isBusy}
          type="button"
          aria-label="Type a command"
        >
          <span className="option-icon"><Type aria-hidden="true" size={27} strokeWidth={1.8} /></span>
          <span>Text</span>
        </button>
      </div>

      <div className="command-response" aria-live="polite">
        {mode === 'text' ? (
          <form className="text-command-form" onSubmit={submitText}>
            <label className="sr-only" htmlFor="command-input">Type your command</label>
            <input
              ref={inputRef}
              id="command-input"
              className="text-command-input"
              value={command}
              onChange={(event) => setCommand(event.target.value)}
              placeholder="Type a command…"
              disabled={isBusy}
            />
            <button className="send-command" type="submit" disabled={isBusy || !command.trim()} aria-label="Send command">
              <Send aria-hidden="true" size={19} strokeWidth={2} />
            </button>
          </form>
        ) : (
          <p className={`command-notice ${listening ? 'is-listening' : ''}`}>{currentNotice}</p>
        )}
      </div>
    </section>
  );
};
