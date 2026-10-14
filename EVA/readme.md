# EVA / Mark L

EVA is a local desktop AI assistant for Windows-focused personal computing. It combines a PyQt6 desktop HUD, Gemini Live voice interaction, file and browser control, proactive monitoring, and a remote dashboard for mobile access.

The codebase is actively evolving, and the project names are used a bit interchangeably across files (`EVA`, `JARVIS`, and `Mark L`). The repository itself is organized around the EVA assistant experience, while the runtime config and environment variables use the `MARK_L_*` naming convention.

## What this project does

- Voice-first assistant workflows using Gemini Live
- Desktop control for apps, windows, mouse, keyboard, and system settings
- Browser and file automation
- Memory and session management
- News, weather, web search, and AI-powered task assistance
- Remote dashboard access for phone/mobile control
- Background monitoring and proactive alerts

## Tech stack

- Python 3.11+
- PyQt6 for the desktop interface
- Google GenAI / Gemini Live for AI responses and native audio
- sounddevice for microphone and speaker streaming
- FastAPI + WebSocket dashboard server
- Playwright, pyautogui, pygetwindow, and related automation libraries
- Memory and document processing utilities for PDF/DOCX/PPTX workflows

## Supported environment

- Primary target: Windows 10 / 11
- Some features are designed to work on macOS or Linux, but Windows is the main supported platform.
- Requires a microphone for voice interactions.
- Requires a Google Gemini API key.

## Quick start

### 1. Clone the project

```bash
git clone <your-repo-url>
cd EVA
```

### 2. Create a virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

If you are setting up the project for the first time, you can also run:

```bash
python setup.py
```

This installs requirements and Playwright dependencies.

### 4. Configure your API key

Use the environment template:

```bash
copy .env.example .env
```

Then edit `.env` and set:

```env
MARK_L_GEMINI_API_KEY=your_gemini_api_key_here
```

You may also set the key through `config/api_keys.json` if your local setup still uses the legacy config file.

### 5. Run the app

```bash
python main.py
```

## Configuration

The project uses environment variables with the `MARK_L_` prefix, defined in `.env.example` and read by `core/config.py`.

Common settings:

```env
MARK_L_GEMINI_API_KEY=your_key
MARK_L_GEMINI_MODEL=models/gemini-2.5-flash-native-audio-preview-12-2025
MARK_L_SEARCH_MODE=search
MARK_L_CACHE_TTL_SECONDS=30
MARK_L_LOG_LEVEL=INFO
MARK_L_TIMEOUT_SECONDS=60.0
MARK_L_ALLOW_BACKGROUND_TASKS=true
MARK_L_ALLOW_WINDOWS_SUBPROCESS_HIDE=true
MARK_L_SAFE_HOME=%USERPROFILE%
MARK_L_MANIFEST_PATH=config/api_keys.json
```

Important: Do not commit real API keys or secrets to the repository. Keep local config files outside version control whenever possible.

## Project structure

```text
EVA/
├── main.py                  # App entry point and orchestration loop
├── ui.py                    # PyQt6 desktop user interface
├── setup.py                 # First-run setup helper
├── setup_check.py           # Environment verification script
├── requirements.txt         # Python dependencies
├── .env.example             # Safe local config template
├── .gitignore
├── actions/                 # Capability modules
│   ├── agent_planner.py
│   ├── background_monitor.py
│   ├── browser_control.py
│   ├── code_helper.py
│   ├── computer_control.py
│   ├── computer_settings.py
│   ├── content_creator.py
│   ├── desktop.py
│   ├── dev_agent.py
│   ├── file_controller.py
│   ├── file_processor.py
│   ├── flight_finder.py
│   ├── game_updater.py
│   ├── image_downloader.py
│   ├── open_app.py
│   ├── proactive.py
│   ├── reminder.py
│   ├── screen_processor.py
│   ├── send_message.py
│   ├── system_monitor.py
│   ├── web_search.py
│   ├── weather_report.py
│   └── youtube_video.py
├── config/                  # Runtime config and app assets
│   ├── api_keys.json
│   ├── jarvis.ico
│   └── certs/
├── core/                    # Core system components
│   ├── audio_engine.py
│   ├── config.py
│   ├── diagnostics.py
│   ├── installer.py
│   ├── intent_router.py
│   ├── latency.py
│   ├── llm_client.py
│   ├── prompt.txt
│   ├── safe_logging.py
│   ├── safe_subprocess.py
│   ├── service_boundaries.py
│   ├── stt.py
│   ├── tts.py
│   └── __init__.py
├── dashboard/               # Remote dashboard server
│   ├── server.py
│   └── static/
├── memory/                  # Local memory storage
│   ├── config_manager.py
│   ├── long_term.json
│   ├── memory_manager.py
│   ├── vector_memory.py
│   └── vector_store.json
├── desktop/                 # Desktop runtime assets
├── test_*.py                # Regression and feature tests
└── README.md
```

## Key capabilities

### Voice and conversation
- Real-time assistant conversation using Gemini Live
- Audio capture and playback with low-latency streaming
- Multilingual support and conversational memory context

### Computer control
- Launch apps
- Control browser tabs and pages
- Manage windows and desktops
- Adjust brightness, volume, and system settings
- Handle keyboard and mouse automation

### File and document workflows
- Read and summarize PDFs, DOCX, PPTX, and text files
- Create documents and reports
- Organize files and folders by voice or automation

### Search, planning, and monitoring
- Web search with fallback modes
- Weather, flight, and general web queries
- Background monitors for tracking topics and updates
- Reminders and proactive check-ins

### Remote dashboard
- Local dashboard served by FastAPI for mobile or remote control
- QR code workflow is exposed in the UI for access pairing

## Validation and diagnostics

Run the project verification script:

```bash
python setup_check.py
```

Run the Python tests:

```bash
python -m pytest -q
```

The project also includes diagnostics helpers in `core/diagnostics.py` for repository-safe health checks.

## Notes

- `main.py` deliberately hides subprocess console windows on Windows to keep the UI clean and avoid noisy terminal windows.
- Logging is sanitized to avoid exposing API tokens, secrets, or sensitive config values.
- The project is primarily designed for personal desktop use and is not a public SaaS deployment.

## License

This project is intended for personal and local assistant use. Review the repository and any included licensing files before redistribution or commercial reuse.
