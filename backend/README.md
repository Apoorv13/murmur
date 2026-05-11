# Murmur Backend

Local-only voice-to-text ML backend for macOS — powered by MLX.

For full documentation, see the [main project README](../README.md).

## Installation

```bash
pip install -e .
```

With development dependencies:

```bash
pip install -e .[dev]
```

## Resource management

The daemon unloads the active model after 60 seconds without transcription or
model-switch activity. Set `MURMUR_IDLE_TIMEOUT_SECONDS` to change the timeout;
use `0` to disable automatic unload.

## License

MIT
