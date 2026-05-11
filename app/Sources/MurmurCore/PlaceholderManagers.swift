import AppKit

public protocol AudioCaptureManaging: AnyObject {
    var isListening: Bool { get }
    var isProcessing: Bool { get }
    var onStateChanged: ((Bool) -> Void)? { get set }
    var onError: ((String) -> Void)? { get set }
    var onTranscription: ((String, Bool) -> Void)? { get set }

    func startListening()
    func stopListening()
    func toggleListening()
}

public final class AudioCaptureManager: AudioCaptureManaging {
    private let audioBridge: AudioBridge

    public private(set) var isListening = false
    public private(set) var isProcessing = false
    public var onStateChanged: ((Bool) -> Void)?
    public var onError: ((String) -> Void)?
    public var onTranscription: ((String, Bool) -> Void)?

    public init(audioBridge: AudioBridge = AudioBridge()) {
        self.audioBridge = audioBridge
    }

    public func startListening() {
        guard !isProcessing, !isListening else {
            return
        }

        isProcessing = true
        Task { [weak self] in
            guard let self else {
                return
            }

            do {
                try await audioBridge.startCapture()
                await MainActor.run {
                    self.isListening = true
                    self.isProcessing = false
                    self.onStateChanged?(true)
                }
            } catch {
                await MainActor.run {
                    self.isListening = false
                    self.isProcessing = false
                    self.onStateChanged?(false)
                    self.onError?(error.localizedDescription)
                }
            }
        }
    }

    public func stopListening() {
        guard !isProcessing, isListening else {
            return
        }

        isProcessing = true
        let activeApplication = NSWorkspace.shared.frontmostApplication
        let bundleID = activeApplication?.bundleIdentifier
        let appName = activeApplication?.localizedName

        Task { [weak self] in
            guard let self else {
                return
            }

            do {
                let response = try await audioBridge.stopAndTranscribe(bundleID: bundleID, appName: appName)
                await MainActor.run {
                    self.isListening = false
                    self.isProcessing = false
                    self.onStateChanged?(false)
                    self.onTranscription?(response.text, response.speechDetected)
                }
            } catch {
                await MainActor.run {
                    self.isListening = false
                    self.isProcessing = false
                    self.onStateChanged?(false)
                    self.onError?(error.localizedDescription)
                }
            }
        }
    }

    public func toggleListening() {
        isListening ? stopListening() : startListening()
    }
}

public protocol PreferencesManaging: AnyObject {
    func openPreferences()
}

public final class PreferencesManager: PreferencesManaging {
    public init() {}

    public func openPreferences() {
        NSApp.activate()

        let alert = NSAlert()
        alert.messageText = "Murmur Preferences"
        alert.informativeText = """
        Push-to-talk defaults to holding Right Option. Grant Accessibility access \
        in Privacy & Security so Murmur can observe the hotkey while other apps \
        are active. Launch at Login uses macOS Login Items when Murmur runs from \
        a signed app bundle. In-app hotkey editing will be added in a future \
        milestone.
        """
        alert.addButton(withTitle: "OK")
        alert.runModal()
    }
}
