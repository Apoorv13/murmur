import AppKit
import ApplicationServices

protocol TextInserting: AnyObject {
    func insert(_ text: String) throws
}

enum TextInsertionError: Error, LocalizedError {
    case missingAccessibilityPermission
    case noFocusedTextField
    case pasteboardUnavailable
    case pasteboardRestoreFailed
    case pasteFallbackFailed

    var errorDescription: String? {
        switch self {
        case .missingAccessibilityPermission:
            "Murmur needs Accessibility permission to insert text into the frontmost app."
        case .noFocusedTextField:
            "No focused text field is available for insertion."
        case .pasteboardUnavailable:
            "The pasteboard was unavailable for fallback text insertion."
        case .pasteboardRestoreFailed:
            "Text was inserted, but Murmur could not restore the previous clipboard contents."
        case .pasteFallbackFailed:
            "Fallback paste insertion failed."
        }
    }
}

enum TextInsertionReadiness: Equatable {
    case ready
    case emptyText
    case missingAccessibilityPermission
    case noFocusedTextField
}

struct TextInsertionReadinessEvaluator {
    static func evaluate(
        text: String,
        accessibilityTrusted: Bool,
        focusedTextElementAvailable: Bool
    ) -> TextInsertionReadiness {
        guard !text.isEmpty else {
            return .emptyText
        }

        guard accessibilityTrusted else {
            return .missingAccessibilityPermission
        }

        guard focusedTextElementAvailable else {
            return .noFocusedTextField
        }

        return .ready
    }
}

protocol AccessibilityPermissionChecking {
    func isProcessTrusted(promptIfNeeded: Bool) -> Bool
}

struct SystemAccessibilityPermissionChecker: AccessibilityPermissionChecking {
    func isProcessTrusted(promptIfNeeded: Bool) -> Bool {
        guard promptIfNeeded else {
            return AXIsProcessTrusted()
        }

        let options = [
            kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true
        ] as CFDictionary

        return AXIsProcessTrustedWithOptions(options)
    }
}

protocol PasteKeystrokePosting {
    func postPasteShortcut() throws
}

struct CGPasteKeystrokePoster: PasteKeystrokePosting {
    private let pasteKeyCode: CGKeyCode = 9

    func postPasteShortcut() throws {
        guard let source = CGEventSource(stateID: .combinedSessionState),
              let keyDown = CGEvent(keyboardEventSource: source, virtualKey: pasteKeyCode, keyDown: true),
              let keyUp = CGEvent(keyboardEventSource: source, virtualKey: pasteKeyCode, keyDown: false)
        else {
            throw TextInsertionError.pasteFallbackFailed
        }

        keyDown.flags = .maskCommand
        keyUp.flags = .maskCommand
        keyDown.post(tap: .cghidEventTap)
        keyUp.post(tap: .cghidEventTap)
    }
}

final class TextInserter: TextInserting {
    private static let pasteboardRestoreDelayMicroseconds: useconds_t = 150_000

    private let permissionChecker: AccessibilityPermissionChecking
    private let systemWideElement: AXUIElement
    private let pasteboard: NSPasteboard
    private let pasteKeystrokePoster: PasteKeystrokePosting

    init(
        permissionChecker: AccessibilityPermissionChecking = SystemAccessibilityPermissionChecker(),
        systemWideElement: AXUIElement = AXUIElementCreateSystemWide(),
        pasteboard: NSPasteboard = .general,
        pasteKeystrokePoster: PasteKeystrokePosting = CGPasteKeystrokePoster()
    ) {
        self.permissionChecker = permissionChecker
        self.systemWideElement = systemWideElement
        self.pasteboard = pasteboard
        self.pasteKeystrokePoster = pasteKeystrokePoster
    }

    func insert(_ text: String) throws {
        try insert(text, promptForAccessibilityPermission: false)
    }

    func insert(_ text: String, promptForAccessibilityPermission: Bool) throws {
        let readiness = TextInsertionReadinessEvaluator.evaluate(
            text: text,
            accessibilityTrusted: permissionChecker.isProcessTrusted(
                promptIfNeeded: promptForAccessibilityPermission
            ),
            focusedTextElementAvailable: true
        )

        switch readiness {
        case .emptyText:
            return
        case .missingAccessibilityPermission:
            throw TextInsertionError.missingAccessibilityPermission
        case .noFocusedTextField:
            throw TextInsertionError.noFocusedTextField
        case .ready:
            break
        }

        let focusedElement = try focusedTextElement()

        do {
            if try insertUsingAccessibility(text, into: focusedElement) {
                return
            }
        } catch TextInsertionError.missingAccessibilityPermission {
            throw TextInsertionError.missingAccessibilityPermission
        } catch {
            throw error
        }

        try insertUsingPasteboardFallback(text)
    }

    private func focusedTextElement() throws -> AXUIElement {
        var focusedElement: AXUIElement?
        let result = withUnsafeMutablePointer(to: &focusedElement) { pointer in
            pointer.withMemoryRebound(to: CFTypeRef?.self, capacity: 1) { reboundPointer in
                AXUIElementCopyAttributeValue(
                    systemWideElement,
                    kAXFocusedUIElementAttribute as CFString,
                    reboundPointer
                )
            }
        }

        guard result == .success else {
            if isMissingPermissionError(result) {
                throw TextInsertionError.missingAccessibilityPermission
            }

            throw TextInsertionError.noFocusedTextField
        }

        guard let focusedElement,
              CFGetTypeID(focusedElement) == AXUIElementGetTypeID()
        else {
            throw TextInsertionError.noFocusedTextField
        }

        guard isLikelyTextInput(focusedElement) else {
            throw TextInsertionError.noFocusedTextField
        }

        return focusedElement
    }

    private func isLikelyTextInput(_ element: AXUIElement) -> Bool {
        if textInputAttributes(element).contains(where: supportedTextAttributeNames.contains) {
            return true
        }

        let role = accessibilityStringAttribute(kAXRoleAttribute, from: element)
        let subrole = accessibilityStringAttribute(kAXSubroleAttribute, from: element)

        return (role.map(textInputRoles.contains) ?? false)
            || (subrole.map(textInputSubroles.contains) ?? false)
    }

    private var supportedTextAttributeNames: Set<String> {
        [
            kAXSelectedTextAttribute,
            kAXSelectedTextRangeAttribute
        ]
    }

    private var textInputRoles: Set<String> {
        [
            kAXTextAreaRole,
            kAXTextFieldRole,
            kAXComboBoxRole
        ]
    }

    private var textInputSubroles: Set<String> {
        [
            kAXSearchFieldSubrole
        ]
    }

    private func textInputAttributes(_ element: AXUIElement) -> [String] {
        var attributeNames: CFArray?
        guard AXUIElementCopyAttributeNames(element, &attributeNames) == .success,
              let attributeNames
        else {
            return []
        }

        return attributeNames as? [String] ?? []
    }

    private func accessibilityStringAttribute(
        _ attributeName: String,
        from element: AXUIElement
    ) -> String? {
        var value: CFTypeRef?
        guard AXUIElementCopyAttributeValue(element, attributeName as CFString, &value) == .success else {
            return nil
        }

        return value as? String
    }

    private func insertUsingAccessibility(_ text: String, into element: AXUIElement) throws -> Bool {
        var isSettable = DarwinBoolean(false)
        let settableResult = AXUIElementIsAttributeSettable(
            element,
            kAXSelectedTextAttribute as CFString,
            &isSettable
        )

        if isMissingPermissionError(settableResult) {
            throw TextInsertionError.missingAccessibilityPermission
        }

        guard settableResult == .success, isSettable.boolValue else {
            return false
        }

        let setResult = AXUIElementSetAttributeValue(
            element,
            kAXSelectedTextAttribute as CFString,
            text as CFString
        )

        if setResult == .success {
            return true
        }

        if isMissingPermissionError(setResult) {
            throw TextInsertionError.missingAccessibilityPermission
        }

        return false
    }

    private func isMissingPermissionError(_ error: AXError) -> Bool {
        error == .apiDisabled
    }

    private func insertUsingPasteboardFallback(_ text: String) throws {
        let snapshot = PasteboardSnapshot.capture(from: pasteboard)

        pasteboard.clearContents()
        guard pasteboard.setString(text, forType: .string) else {
            _ = snapshot.restore(to: pasteboard)
            throw TextInsertionError.pasteboardUnavailable
        }

        do {
            try pasteKeystrokePoster.postPasteShortcut()
            usleep(Self.pasteboardRestoreDelayMicroseconds)
        } catch {
            _ = snapshot.restore(to: pasteboard)
            throw error
        }

        guard snapshot.restore(to: pasteboard) else {
            throw TextInsertionError.pasteboardRestoreFailed
        }
    }
}

private struct PasteboardSnapshot {
    private struct Item {
        let typeData: [(NSPasteboard.PasteboardType, Data)]

        func pasteboardItem() -> NSPasteboardItem {
            let item = NSPasteboardItem()
            typeData.forEach { type, data in
                item.setData(data, forType: type)
            }
            return item
        }
    }

    private let items: [Item]

    static func capture(from pasteboard: NSPasteboard) -> PasteboardSnapshot {
        let items = pasteboard.pasteboardItems?.map { pasteboardItem in
            Item(
                typeData: pasteboardItem.types.compactMap { type in
                    guard let data = pasteboardItem.data(forType: type) else {
                        return nil
                    }

                    return (type, data)
                }
            )
        } ?? []

        return PasteboardSnapshot(items: items)
    }

    func restore(to pasteboard: NSPasteboard) -> Bool {
        pasteboard.clearContents()

        guard !items.isEmpty else {
            return true
        }

        return pasteboard.writeObjects(items.map { $0.pasteboardItem() })
    }
}
