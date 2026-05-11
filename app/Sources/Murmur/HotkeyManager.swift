import AppKit
import ApplicationServices
import MurmurCore

protocol HotkeyPermissionChecking: AnyObject {
    var isTrustedForGlobalKeyEvents: Bool { get }

    @discardableResult
    func requestGlobalKeyEventAccess() -> Bool
}

final class AccessibilityHotkeyPermissionChecker: HotkeyPermissionChecking {
    var isTrustedForGlobalKeyEvents: Bool {
        AXIsProcessTrusted()
    }

    func requestGlobalKeyEventAccess() -> Bool {
        let options = [
            kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true
        ] as CFDictionary

        return AXIsProcessTrustedWithOptions(options)
    }
}

final class HotkeyManager {
    private var configuration: HotkeyConfiguration
    private let permissionChecker: HotkeyPermissionChecking
    private let onPress: () -> Void
    private let onRelease: () -> Void
    private var matcher = HotkeyMatcher()
    private var globalMonitor: Any?
    private var localMonitor: Any?

    private(set) var hasRequiredPermissions: Bool

    init(
        configuration: HotkeyConfiguration,
        permissionChecker: HotkeyPermissionChecking = AccessibilityHotkeyPermissionChecker(),
        onPress: @escaping () -> Void,
        onRelease: @escaping () -> Void
    ) {
        self.configuration = configuration
        self.permissionChecker = permissionChecker
        self.onPress = onPress
        self.onRelease = onRelease
        hasRequiredPermissions = permissionChecker.isTrustedForGlobalKeyEvents
    }

    deinit {
        stop()
    }

    func start() {
        guard globalMonitor == nil, localMonitor == nil else {
            return
        }

        hasRequiredPermissions = permissionChecker.requestGlobalKeyEventAccess()

        let mask: NSEvent.EventTypeMask = [.keyDown, .keyUp, .flagsChanged]
        globalMonitor = NSEvent.addGlobalMonitorForEvents(matching: mask) { [weak self] event in
            self?.handle(event)
        }
        localMonitor = NSEvent.addLocalMonitorForEvents(matching: mask) { [weak self] event in
            self?.handle(event)
            return event
        }
    }

    func stop() {
        if let globalMonitor {
            NSEvent.removeMonitor(globalMonitor)
            self.globalMonitor = nil
        }

        if let localMonitor {
            NSEvent.removeMonitor(localMonitor)
            self.localMonitor = nil
        }
    }

    func updateConfiguration(_ configuration: HotkeyConfiguration) {
        self.configuration = configuration
        matcher = HotkeyMatcher()
    }

    func refreshPermissionStatus() {
        hasRequiredPermissions = permissionChecker.isTrustedForGlobalKeyEvents
    }

    private func handle(_ event: NSEvent) {
        guard let hotkeyEvent = HotkeyEvent(event: event),
              let activation = matcher.activation(
                  for: hotkeyEvent,
                  configuration: configuration
              ) else {
            return
        }

        let callback = activation == .pressed ? onPress : onRelease
        if Thread.isMainThread {
            callback()
        } else {
            DispatchQueue.main.async(execute: callback)
        }
    }
}

private extension HotkeyEvent {
    init?(event: NSEvent) {
        guard let kind = HotkeyEventKind(eventType: event.type) else {
            return nil
        }

        self.init(
            kind: kind,
            keyCode: event.keyCode,
            modifierFlags: HotkeyModifierFlags(eventModifierFlags: event.modifierFlags),
            isRepeat: event.isARepeat
        )
    }
}

private extension HotkeyEventKind {
    init?(eventType: NSEvent.EventType) {
        switch eventType {
        case .keyDown:
            self = .keyDown
        case .keyUp:
            self = .keyUp
        case .flagsChanged:
            self = .flagsChanged
        default:
            return nil
        }
    }
}

private extension HotkeyModifierFlags {
    init(eventModifierFlags: NSEvent.ModifierFlags) {
        var flags: HotkeyModifierFlags = []

        if eventModifierFlags.contains(.shift) {
            flags.insert(.shift)
        }

        if eventModifierFlags.contains(.control) {
            flags.insert(.control)
        }

        if eventModifierFlags.contains(.option) {
            flags.insert(.option)
        }

        if eventModifierFlags.contains(.command) {
            flags.insert(.command)
        }

        if eventModifierFlags.contains(.function) {
            flags.insert(.function)
        }

        self = flags
    }
}
