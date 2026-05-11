# Murmur macOS App

This directory contains the initial Swift scaffold for Murmur's macOS menu bar app.
It is intentionally small and OSS-friendly: a Swift Package executable with AppKit
source files, no generated Xcode project files, and an `Info.plist` ready for a
future app bundle target.

## Build validation

```bash
cd app
swift build
```

`swift build` validates the AppKit source and menu bar controller. Swift Package
Manager builds an executable, not a signed `.app` bundle, so `Info.plist` is not
applied by this validation path. The plist includes `LSUIElement` for no Dock icon
and privacy purpose strings for the future bundled app.

## Current behavior

- Runs as an accessory app with no Dock icon.
- Adds a menu bar status item.
- Provides placeholder menu items for Start Listening, Preferences, and Quit.
- Includes a `TextInserter` service that inserts text into the focused text field
  of the frontmost app via Accessibility APIs, with a clipboard-preserving
  Cmd+V fallback when direct AX insertion is unavailable.
- Adds a global push-to-talk hotkey manager. Holding Right Option starts
  listening; releasing it stops listening.

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
