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

# Set up the backend, then start the daemon and development menu bar app
scripts/murmur-dev setup
scripts/murmur-dev start

# Optional: open the TUI control panel in this terminal
scripts/murmur-dev tui
```

Useful development commands:

```bash
scripts/murmur-dev status
scripts/murmur-dev stop
scripts/murmur-dev restart
```

To have Murmur ready automatically when you log in:

```bash
scripts/murmur-dev install-agent
```

That LaunchAgent starts both the backend daemon and the development SwiftPM menu
bar app. If you only want the backend daemon to autostart, use:

```bash
scripts/murmur-dev install-agent --daemon-only
```

The SwiftPM menu bar app is still a development executable, not a signed `.app`
bundle. The in-app Launch at Login toggle remains disabled until Murmur is
packaged as a signed app bundle, but the development LaunchAgent above works for
local testing.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## Security

See [SECURITY.md](SECURITY.md) for vulnerability reporting.

## License

[MIT](LICENSE)
