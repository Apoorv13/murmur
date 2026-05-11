import AppKit

protocol AudioCaptureManaging: AnyObject {
    var isListening: Bool { get }
    func startListening()
    func stopListening()
    func toggleListening()
}

final class AudioCaptureManager: AudioCaptureManaging {
    private(set) var isListening = false

    func startListening() {
        isListening = true
    }

    func stopListening() {
        isListening = false
    }

    func toggleListening() {
        isListening ? stopListening() : startListening()
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
        alert.informativeText = """
        Push-to-talk defaults to holding Right Option. Grant Accessibility access \
        in Privacy & Security so Murmur can observe the hotkey while other apps \
        are active. In-app hotkey editing will be added in a future milestone.
        """
        alert.addButton(withTitle: "OK")
        alert.runModal()
    }
}
