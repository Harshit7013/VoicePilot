# VoicePilot — Offline Voice-Controlled Desktop Task Automation
## Problem Statement TH2-PS-GAI-021 | Domain: Generative AI | Approach: Offline-first & Privacy-first

<div align="center">

```
🎙️ Voice Command → 🧠 Local LLM → 📋 Action Plan → ⚡ Verified Execution
```

**Privacy-first · Action-oriented · Self-recovering · Offline by default**

</div>

---

## Architecture at a Glance

```
voicepilot/
├── agent/
│   ├── providers/          # STT (Whisper) · LLM (Ollama) · TTS (Piper)
│   ├── planner/            # JSON action planning + Pydantic schemas
│   ├── safety/             # Risk classifier + policy gate (HITL)
│   ├── executor/           # Desktop (PyAutoGUI) · Browser (Playwright) · Files (pathlib)
│   ├── observer/           # Screenshots + PaddleOCR verification
│   ├── recovery/           # 5-stage recovery (Retry → Re-plan → Escalate)
│   ├── metrics/            # SQLite reliability metrics
│   ├── audio/              # Microphone capture (sounddevice)
│   ├── core.py             # 11-stage orchestration loop
│   └── api.py              # FastAPI + WebSocket bridge
├── apps/desktop/           # React + Vite UI (Tauri-ready)
├── cli.py                  # Terminal interface
└── tests/                  # pytest test suite
```

## 11-Stage Execution Loop

```
1. 🎙️  Listen        → Capture voice from microphone
2. 📝  Transcribe    → faster-whisper (local, offline)
3. 🧠  Plan          → Ollama LLM generates structured JSON plan
4. 🔒  Validate      → Risk classifier + policy gate (HITL for high-risk)
5. ⚡  Execute       → Trusted tools: PyAutoGUI / Playwright / pathlib
6. 📸  Observe       → Screenshot + PaddleOCR state capture
7. ✅  Verify        → Compare actual vs expected outcome
8. 🔄  Recover       → Retry → Alternative → Re-establish → Re-plan → Escalate
9. 📊  Complete      → Record metrics, speak result via Piper TTS
```

## Quick Start

### 1. Install Python dependencies

```bash
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium
```

### 2. Install & start Ollama

```bash
# macOS / Linux
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:7b
```

### 3. Start the agent API server

```bash
python -m agent.api
# Server starts at http://localhost:8765
```

### 4a. Start the UI (Vite dev server)

```bash
cd apps/desktop
npm install
npm run dev
# Open http://localhost:5173
```

### 4b. Or use the CLI (no UI required)

```bash
python cli.py
```

### 5. Run the offline demo

Turn off Wi-Fi, then say or type:
> *"Create a folder named Hackathon Demo with a text file saying VoicePilot works offline."*

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| UI | React + Vite | Task display, voice control, confirmations |
| Runtime | Python + FastAPI | Agent orchestration + WebSocket bridge |
| STT | faster-whisper | Local speech-to-text (no internet) |
| LLM | Ollama + Qwen2.5 | Local planning (no internet) |
| TTS | Piper / macOS say | Local text-to-speech (no internet) |
| Desktop | PyAutoGUI | GUI automation |
| Browser | Playwright | Web automation |
| Files | pathlib / shutil | File operations |
| OCR | PaddleOCR | Verification |
| DB | SQLite + aiosqlite | Metrics + task history |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WHISPER_MODEL` | `base` | Whisper model size (tiny/base/small/medium) |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Ollama model to use |
| `AUTO_APPROVE_MEDIUM` | `false` | Auto-approve medium-risk actions |

## Hardware Requirements

- **Minimum**: 8 GB RAM, Intel/AMD CPU, SSD
- **Recommended**: 16 GB RAM, Intel 13th-gen P-series CPU, NVMe SSD
- **GPU**: Not required (CPU-first design)
- **Internet**: Not required after model download

## Safety Model

| Risk Level | Examples | Policy |
|-----------|---------|--------|
| 🟢 LOW | Open app, read file, search | Auto-execute |
| 🟡 MEDIUM | Create file, move, rename | Configurable (default: auto) |
| 🔴 HIGH | Delete file, send message | Always requires confirmation |

## API Reference

```
GET  /              → Health check
POST /command       → Submit text command (async)
POST /command/sync  → Submit text command (blocking)
POST /audio         → Submit base64 audio
POST /confirm/{id}  → Approve/deny a confirmation
GET  /tasks         → Task history
GET  /metrics       → Reliability metrics
WS   /ws            → Real-time event stream
```

## Run Tests

```bash
pip install pytest pytest-asyncio
python -m pytest tests/ -v
```

## Demo Tasks

1. **Offline file creation**: "Create a folder named Hackathon Demo with a text file saying VoicePilot works offline."
2. **Desktop automation**: "Open Calculator and compute 125 × 48"
3. **File management**: "Find PDF files in Downloads and move them to Desktop"
4. **App control**: "Open VS Code, create hello.py with print('Hello World'), and verify the file exists"

---

*VoicePilot: Plan → Validate → Execute → Observe → Verify → Recover*
