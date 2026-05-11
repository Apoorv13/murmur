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

Accessibility permission is requested through macOS when future text insertion
code calls the Accessibility APIs; there is no separate app-level permission flow
in this scaffold yet.
