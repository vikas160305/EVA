# 🤖 EVA — AI Desktop Assistant
### Powered by Gemini Live API · Real-time Voice · Full PC Control

> A conversational AI assistant that hears you, sees your screen, remembers your context, and controls your computer — entirely by voice.

---

## ✨ What is EVA?

EVA is a local, voice-first AI assistant built on top of Google''s **Gemini Live API**. It runs as a native desktop application (PyQt6 HUD) and gives you a hands-free, always-available assistant that can:

- Hold natural, real-time voice conversations in **any language**
- Control your entire PC — apps, files, browser, volume, window management
- Remember who you are, what you''re working on, and what you discussed yesterday
- Watch topics in the background and brief you proactively

No monthly subscription. No cloud lock-in beyond the Gemini API key. Everything runs locally.

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone <your-repo-url>
cd EVA
pip install -r requirements.txt
```

### 2. Configure your API key

Copy the environment template and fill in your Gemini key:

```bash
cp .env.example .env
# Edit .env and set MARK_L_GEMINI_API_KEY=<your key>
```

Or set it directly in `config/api_keys.json`:

```json
{
  "gemini_api_key": "YOUR_KEY_HERE",
  "assistant_name": "EVA",
  "user_name": "Your Name"
}
```

Get a free Gemini API key at [aistudio.google.com](https://aistudio.google.com).

### 3. Run

```bash
python main.py
```

---

## 📋 Requirements

| Requirement | Details |
|---|---|
| **OS** | Windows 10/11 (macOS / Linux partially supported) |
| **Python** | 3.11 or 3.12 |
| **Microphone** | Required for voice interaction |
| **API Key** | Free Gemini API key |

### Python Dependencies

```bash
pip install -r requirements.txt
```

### Optional — Better Document Conversion

For accurate DOCX / PPTX ↔ PDF conversions, install LibreOffice and add it to your PATH:

- **Download:** https://www.libreoffice.org/download/download/

Then install the extra Python packages:

```bash
pip install python-docx python-pptx reportlab PyPDF2 Pillow docx2pdf comtypes pywin32
```

> ⚠️ Some OS-specific packages (like `pycaw`, `pywin32`) are Windows-only and will not install on macOS/Linux — this is expected.

Run `python setup_check.py` to verify your full environment.

---

## 🎛️ Capabilities

### 🎙️ Voice & Conversation
| Feature | Description |
|---|---|
| Real-time Voice | Ultra-low latency via Gemini Live API |
| Wake Word | Offline "Hey EVA" detection — Gemini only activates after the phrase |
| Hybrid Input | Seamlessly switch between voice and keyboard |
| Multilingual | Detects your language on first use; all sessions adapt automatically |

### 🖥️ PC Control
| Feature | Description |
|---|---|
| App Launcher | Open any application by name |
| System Settings | Adjust volume, brightness, WiFi, and power by voice |
| Computer Control | Keyboard shortcuts, mouse movement, and window management |
| Desktop Control | Taskbar, window switching, and desktop-level operations |
| Browser Control | Open URLs, navigate tabs, interact with web pages by voice |

### 🧠 Memory & Context
| Feature | Description |
|---|---|
| Persistent Memory | Remembers your projects, preferences, and personal context |
| Session Summaries | Summarizes each conversation; briefs you next morning then clears itself |
| Vector Memory | Semantic search over long-term memory for relevant context retrieval |

### 🌐 Web & Search
| Feature | Description |
|---|---|
| Multi-Mode Search | news / research / price / compare — Gemini Grounded + DDG fallback |
| Parallel News | Runs Gemini + DuckDuckGo simultaneously; fastest result wins |
| Flight Finder | Live flight price and availability lookup |
| Weather Report | Live weather for your city, personalized from memory |

### 📂 File & Document
| Feature | Description |
|---|---|
| File Controller | Create, rename, move, copy, delete files and folders by voice |
| File Processor | Read, summarize, and Q&A over local documents (PDF, DOCX, PPTX, TXT) |
| Content Creator | Generate and save documents, reports, and text files |

### 👁️ Vision
| Feature | Description |
|---|---|
| Screen Awareness | Real-time screen capture piped into Gemini |
| Webcam Vision | Webcam feed available for visual context |

### 🔔 Proactive & Background
| Feature | Description |
|---|---|
| Morning Briefing | On first boot: greets you, reads the time, recaps yesterday, fetches news |
| Proactive 2.0 | Time/context-aware check-ins — rotates topics, 20-min cooldown |
| Background Monitor | Watches any topic — checks for new headlines daily |
| Smart Reminders | OS-native scheduled notifications |
| System Monitor | Continuous CPU, RAM, GPU & temperature telemetry with voice alerts |

### 🛠️ Developer & Extras
| Feature | Description |
|---|---|
| Code Helper | Inline code review, debugging, and generation |
| Dev Agent | Autonomous developer task agent |
| YouTube Control | Search, play, and control YouTube playback by voice |
| Send Message | Compose messages through WhatsApp, Telegram, and more |
| Game Updater | Checks and triggers updates on Steam and Epic Games |
| Clipboard Intelligence | Copy text → panel with Translate / Summarize / Explain / Fix |
| Remote Dashboard | Control EVA from your phone via QR code pairing |
| Auto-Start | Registers with OS startup (Windows Registry / LaunchAgent) |
| Assistant Customization | Change assistant name and your name from the UI at runtime |

---

## 🗂️ Project Structure

```
EVA/
├── main.py                   # Core loop — Gemini Live session, audio I/O, tool dispatch
├── ui.py                     # PyQt6 HUD — waveform, log panel, camera feed, interrupt
├── setup.py                  # First-run installer (pip + playwright + pywin32)
├── setup_check.py            # Environment verification script
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template (copy to .env)
├── .gitignore
│
├── actions/                  # Skill modules — one file per capability domain
│   ├── web_search.py         # Gemini + DDG parallel search
│   ├── screen_processor.py   # Screen capture & webcam vision
│   ├── background_monitor.py # Daily topic watching (no crypto)
│   ├── proactive.py          # Proactive 2.0 engine
│   ├── reminder.py           # OS-native scheduled notifications
│   ├── system_monitor.py     # CPU / RAM / GPU / temperature
│   ├── computer_settings.py  # Volume, brightness, WiFi, power
│   ├── computer_control.py   # Keyboard shortcuts, mouse, window management
│   ├── open_app.py           # Application launcher
│   ├── browser_control.py    # Web browser automation
│   ├── file_controller.py    # File system operations
│   ├── file_processor.py     # Document reading and summarization
│   ├── content_creator.py    # Document and text generation
│   ├── send_message.py       # Messaging integration
│   ├── weather_report.py     # Live weather data
│   ├── flight_finder.py      # Flight search
│   ├── youtube_video.py      # YouTube playback control
│   ├── game_updater.py       # Steam / Epic game update management
│   ├── code_helper.py        # Code review and generation
│   ├── dev_agent.py          # Developer task agent
│   ├── image_downloader.py   # Image download with public-URL validation
│   ├── agent_planner.py      # High-level multi-step goal planner
│   └── desktop.py            # Desktop and taskbar control
│
├── memory/                   # Persistent memory layer
│   ├── memory_manager.py     # Load/save long_term.json
│   ├── vector_memory.py      # Semantic search over memory entries
│   ├── config_manager.py     # Memory configuration helpers
│   ├── long_term.json        # Persistent store (identity, preferences, projects)
│   └── vector_store.json     # Vector memory index
│
├── core/                     # Shared engine components
│   ├── llm_client.py         # Provider routing, model selection, prompt formatting
│   ├── tts.py                # Text-to-speech engine
│   ├── stt.py                # Speech-to-text engine
│   ├── intent_router.py      # Fast intent matching (pre-Gemini dispatch)
│   ├── audio_engine.py       # Queued audio playback and microphone capture
│   ├── latency.py            # Turn trace & latency measurement
│   ├── safe_logging.py       # Structured, sanitized logging (no secrets)
│   ├── safe_subprocess.py    # List-style subprocess with timeouts
│   ├── service_boundaries.py # Service ownership definitions
│   ├── diagnostics.py        # Repo-safe health report
│   ├── installer.py          # Dependency installation helpers
│   ├── config.py             # Typed, env-backed configuration layer
│   └── prompt.txt            # Assistant personality and tool-routing rules
│
├── config/                   # Runtime configuration
│   ├── api_keys.json         # API key, OS setting, assistant name, user name
│   ├── jarvis.ico            # Application icon
│   └── certs/                # Local TLS certs for dashboard (never commit real certs)
│
└── dashboard/                # Remote phone dashboard
    ├── server.py             # FastAPI + WebSocket server
    └── static/               # Web UI assets served to the phone
```

---

## ⚙️ Configuration

| Variable | Default | Description |
|---|---|---|
| `MARK_L_GEMINI_API_KEY` | — | **Required.** Your Gemini API key |
| `MARK_L_GEMINI_MODEL` | `gemini-2.5-flash-native-audio-preview` | Model to use |
| `MARK_L_SEARCH_MODE` | `search` | Default search mode |
| `MARK_L_CACHE_TTL_SECONDS` | `30` | In-process search cache TTL |
| `MARK_L_LOG_LEVEL` | `INFO` | Logging verbosity |
| `MARK_L_TIMEOUT_SECONDS` | `60.0` | Request timeout |
| `MARK_L_ALLOW_BACKGROUND_TASKS` | `true` | Enable proactive / monitoring |
| `MARK_L_SAFE_HOME` | `$HOME` | Root directory for file operations |

> ⚠️ **Never commit `.env` or real API keys.** Use `.env.example` as the template only.

---

## 🧪 Testing & Diagnostics

Run the test suite:

```bash
python -m pytest -q
```

Run a repository-safe diagnostics report (no keys or secrets printed):

```bash
python -m core.diagnostics --report
```

Run the latency benchmark (no microphone or network required):

```bash
python -m core.latency --benchmark --iterations 100
```

---

## 🏗️ Architecture Notes

- **No console windows** — `main.py` patches `subprocess.Popen` globally with `CREATE_NO_WINDOW` on Windows.
- **Atomic file writes** — file creation uses a validated temp file then atomically replaces the target.
- **Secret scrubbing** — all logging passes through `core.safe_logging`, which strips API keys, tokens, and certificate fields before output.
- **Cancellation-safe queues** — audio and UI writes go through bounded, cancellation-aware queues so stale turns cannot deliver stale speech or UI updates.
- **Retry policy** — only retries transient failures (HTTP 429, 5xx, timeout, connection reset). Never retries cancellations or invalid requests.

---

## 🙋 Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` | `pip install <module_name>` — some OS packages are not in `requirements.txt` |
| No audio output | Check your default audio device in system settings |
| Wake word not triggering | Speak clearly; check microphone permissions |
| File operations fail | Ensure `MARK_L_SAFE_HOME` points to a writable directory |
| Dashboard QR not showing | Make sure `uvicorn` is installed and port 8000 is free |

---

## ⚠️ License

Personal and non-commercial use only.
Licensed under **[Creative Commons BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)**.
