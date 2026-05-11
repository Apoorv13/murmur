import AppKit

protocol AudioCaptureManaging: AnyObject {
    var isListening: Bool { get }
    func toggleListening()
}

final class AudioCaptureManager: AudioCaptureManaging {
    private(set) var isListening = false

    func toggleListening() {
        isListening.toggle()
    }
}

protocol PreferencesManaging: AnyObject {
    func openPreferences()
}

final class PreferencesManager: PreferencesManaging {
    func openPreferences() {
        NSApp.activate()

        let alert = NSAlert()
        alert.messageText = "Murmur Preferences"
        alert.informativeText = "Preferences will be added in a future milestone."
        alert.addButton(withTitle: "OK")
        alert.runModal()
    }
}
