# Murmur

**Local-only, privacy-first voice-to-text for macOS** — optimized for Apple Silicon.

Murmur transcribes your speech and inserts text directly into any app at your cursor. No cloud. No latency. No compromises.

## Features

- 🎙️ **Push-to-talk** — hold a hotkey, speak, release to transcribe
- ⚡ **Low latency** — ~500ms end-to-end on Apple Silicon (M-series)
- 🔒 **100% local** — zero network calls, all audio stays on your device
- 🖥️ **Universal text insertion** — works in any app (IDE, terminal, browser, etc.)
- 🧠 **Context-aware** — adjusts vocabulary based on active application
- 🔄 **Fluid model selection** — hot-swap between Whisper and Parakeet models via TUI
- 📊 **TUI control panel** — monitor stats, switch models, view transcription history

## Architecture

```
Swift Menu Bar App (system integration)
       ↕ Unix Socket IPC
Python ML Backend (Whisper/Parakeet via MLX)
       ↕ Unix Socket IPC
TUI Control Panel (Textual — monitoring & control)
```

## Supported Models

| Model | Family | Speed | Accuracy | RAM |
|-------|--------|-------|----------|-----|
| whisper-tiny | Whisper | ~0.4s | Good | ~150MB |
| whisper-base | Whisper | ~0.5s | Better | ~300MB |
| whisper-small | Whisper | ~0.8s | Great | ~900MB |
| parakeet-tdt-0.6b-v2 | Parakeet | ~0.13s | Best (1.67% WER) | ~2.5GB |
| parakeet-tdt-0.6b-v3 | Parakeet | ~0.15s | Great (multilingual) | ~2.5GB |

## Requirements

- macOS 14+ (Sonoma or later)
- Apple Silicon (M1/M2/M3/M4)
- Python 3.11+
- Xcode 15+ (for Swift app)
- Accessibility permissions (for text insertion)

## Quick Start

```bash
# Clone
git clone https://github.com/yourusername/murmur.git
cd murmur

# Set up Python backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Start the daemon
murmur-daemon start

# Launch TUI control panel
murmur-tui
```

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## Security

See [SECURITY.md](SECURITY.md) for vulnerability reporting.

## License

[MIT](LICENSE)
