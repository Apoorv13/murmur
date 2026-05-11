# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| latest  | ✅                 |

## Core Security Principles

Murmur is built on these non-negotiable security principles:

1. **Local-only processing** — No audio data ever leaves your device
2. **No network calls** — The application makes zero outbound connections
3. **No telemetry** — No usage tracking or analytics
4. **Minimal persistence** — Audio is processed in-memory and discarded
5. **Restricted IPC** — Unix socket with owner-only permissions (0600)

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do NOT** open a public issue
2. Email: [security contact to be configured]
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

## Response Timeline

- **Acknowledgment**: Within 48 hours
- **Assessment**: Within 7 days
- **Fix**: Depends on severity (critical: 24-72 hours, high: 1 week, medium: 2 weeks)

## Scope

The following are in scope for security reports:

- Audio data leakage (any path where audio leaves the device)
- Unauthorized access to the IPC socket
- Code execution via crafted audio or model files
- Privilege escalation through accessibility permissions
- Dependency vulnerabilities that affect Murmur's security posture

## Out of Scope

- Attacks requiring physical access to the machine
- Social engineering
- Denial of service against local resources (user's own machine)
