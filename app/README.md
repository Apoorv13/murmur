# Murmur macOS App

This directory contains Murmur's Swift Package menu bar app. It builds an
accessory AppKit executable plus a small core module for shared app services,
audio capture, and IPC.

## Build validation

```bash
cd app
swift build
swift run MurmurIPCFramingChecks
```

`swift build` validates the AppKit app, AVFoundation audio bridge, and IPC check
executable. `MurmurIPCFramingChecks` verifies the daemon framing contract and the
float32 base64 payload used for transcription without requiring microphone
hardware.

Swift Package Manager builds an executable, not a signed `.app` bundle, so
`Info.plist` is not applied by this validation path. The plist includes
`LSUIElement` for no Dock icon and privacy purpose strings for the future bundled
app.

## Current behavior

- Runs as an accessory app with no Dock icon.
- Adds a menu bar status item with idle, listening, processing, and error
  status rendering plus active-app context in the tooltip.
- Captures microphone audio in memory with AVFoundation while listening.
- Sends captured float32 audio to the local Python daemon over its Unix socket
  using a 4-byte big-endian length prefix and JSON payload.
- Surfaces microphone permission, capture, and daemon IPC errors with alerts.
- Provides a Launch at Login menu item backed by `ServiceManagement.SMAppService`
  when Murmur is running from a signed `.app` bundle.
- Includes a `TextInserter` service that inserts text into the focused text field
  of the frontmost app via Accessibility APIs, with a clipboard-preserving
  Cmd+V fallback when direct AX insertion is unavailable.
- Adds a global push-to-talk hotkey manager. Holding Right Option starts
  listening; releasing it stops listening.

Audio is not persisted and the Swift app does not make network calls.
Accessibility permission is required for text insertion. `TextInserter` reports
explicit errors when permission is missing or when no focused text field is
available.

## Push-to-talk hotkey

The default push-to-talk binding is Right Option. macOS reports left and right
Option as separate `flagsChanged` key codes in this scaffold, so the default uses
the right-side virtual key code directly. If a future keyboard layout or event
source cannot provide side-specific modifier key codes, the `HotkeyConfiguration`
abstraction can fall back to another modifier or key binding without changing
the event monitoring code.

Global key monitoring requires Accessibility access in System Settings >
Privacy & Security > Accessibility. Murmur prompts for that access on launch and
also shows a menu item linking to the relevant privacy settings when permission
is still needed. Local and global event monitors always pass events through; the
manager only invokes callbacks when the configured hotkey transitions between
pressed and released.

The hotkey can be configured through `UserDefaultsHotkeyConfigurationStore` by
setting `PushToTalkHotkeyKeyCode`, `PushToTalkHotkeyTriggerKind`,
`PushToTalkHotkeyRequiredModifiers`, and `PushToTalkHotkeyDisplayName`.
`PushToTalkHotkeyTriggerKind` accepts `modifier` or `key`; modifier values use a
bitmask of shift `1`, control `2`, option `4`, command `8`, and function `16`.

## Launch at Login

The menu bar app exposes a Launch at Login toggle through
`LaunchAtLoginController`. It uses `SMAppService.mainApp` and stores no custom
state outside the macOS Login Items registration.

Swift Package Manager builds Murmur as a raw executable, not a signed `.app`
bundle, so the local `swift build` artifact cannot register itself as a login
item. In that mode the controller reports an explicit unsupported state and the
menu item is disabled with the bundle requirement. A future Xcode or packaging
target should apply `Info.plist`, provide `CFBundleIdentifier`, sign the app
bundle, and then the same controller will register/unregister the main app login
item. If macOS reports `requiresApproval`, Murmur opens System Settings >
General > Login Items for the user to approve the registration.
