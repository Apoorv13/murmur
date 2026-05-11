# Contributing to Murmur

Thank you for your interest in contributing to Murmur! This document provides guidelines for contributing.

## Development Setup

### Prerequisites

- macOS 14+ (Sonoma or later) on Apple Silicon
- Python 3.11+
- Xcode 15+ (for Swift components)
- Git

### Getting Started

```bash
# Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/murmur.git
cd murmur

# Set up the Python backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check .
mypy .
```

## Development Workflow

### Branch Naming

- `feat/<feature-name>` — new features
- `fix/<description>` — bug fixes
- `docs/<topic>` — documentation updates
- `refactor/<scope>` — code refactoring
- `test/<scope>` — adding or improving tests

### Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

[optional body]

[optional footer]
```

**Types:** `feat`, `fix`, `docs`, `refactor`, `test`, `ci`, `chore`
**Scopes:** `engine`, `audio`, `tui`, `swift`, `config`, `ci`

**Examples:**
```
feat(engine): add parakeet TDT model adapter
fix(audio): handle microphone permission denial gracefully
docs(readme): add model comparison table
```

### Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with clear, atomic commits
3. Ensure all tests pass and linting is clean
4. Open a PR with a clear description
5. Fill out the security review checklist in the PR template
6. Request review
7. Squash merge after approval

## Code Style

### Python
- Formatter: `ruff format`
- Linter: `ruff check`
- Type checking: `mypy` (strict mode)
- Target: Python 3.11+

### Swift
- Linter: SwiftLint
- Follow Apple's [Swift API Design Guidelines](https://www.swift.org/documentation/api-design-guidelines/)

## Security Considerations

Since Murmur processes audio and has system-level access:

- Never introduce network calls (local-only is a core promise)
- Never persist audio data without explicit user consent
- Keep IPC socket permissions restrictive (0600)
- Audit new dependencies before adding
- Never use `eval`/`exec` on untrusted input
- Load model files only from trusted, configured paths

## Testing

- Write tests for all new functionality
- Test edge cases (no microphone, permission denied, model not found)
- Performance tests for latency-critical paths

## Questions?

Open an issue for discussion before starting large changes.
