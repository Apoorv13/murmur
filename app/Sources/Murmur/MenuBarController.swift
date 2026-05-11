import AppKit
import MurmurCore

final class MenuBarController: NSObject {
    private let audioManager: AudioCaptureManaging
    private let preferencesManager: PreferencesManaging
    private let appContextDetector: AppContextDetecting
    private let hotkeyConfiguration: HotkeyConfiguration
    private let statusItem: NSStatusItem
    private let startListeningItem = NSMenuItem()
    private let hotkeyStatusItem = NSMenuItem()
    private let permissionItem = NSMenuItem()
    private var hotkeyManager: HotkeyManager?

    init(
        audioManager: AudioCaptureManaging,
        preferencesManager: PreferencesManaging,
        appContextDetector: AppContextDetecting = AppContextDetector(),
        hotkeyConfiguration: HotkeyConfiguration = UserDefaultsHotkeyConfigurationStore()
            .loadPushToTalkHotkey(),
        statusBar: NSStatusBar = .system
    ) {
        self.audioManager = audioManager
        self.preferencesManager = preferencesManager
        self.appContextDetector = appContextDetector
        self.hotkeyConfiguration = hotkeyConfiguration
        statusItem = statusBar.statusItem(withLength: NSStatusItem.variableLength)
        super.init()
        configureAudioManagerCallbacks()
        hotkeyManager = HotkeyManager(
            configuration: hotkeyConfiguration,
            onPress: { [weak self] in
                self?.startPushToTalk()
            },
            onRelease: { [weak self] in
                self?.stopPushToTalk()
            }
        )
        hotkeyManager?.start()
        configureStatusItem()
    }

    private func configureStatusItem() {
        if let button = statusItem.button {
            button.image = NSImage(systemSymbolName: "waveform", accessibilityDescription: "Murmur")
            button.imagePosition = .imageLeading
            button.toolTip = "Murmur"
        }

        statusItem.menu = buildMenu()
        updateMenuState()
        refreshAppContextTooltip()
    }

    private func configureAudioManagerCallbacks() {
        audioManager.onStateChanged = { [weak self] _ in
            self?.updateMenuState()
        }
        audioManager.onError = { [weak self] message in
            self?.showAlert(title: "Murmur Audio Error", message: message)
        }
        audioManager.onTranscription = { [weak self] text, speechDetected in
            let message = speechDetected && !text.isEmpty ? text : "No speech detected."
            self?.showAlert(title: "Murmur Transcription", message: message)
        }
    }

    private func buildMenu() -> NSMenu {
        let menu = NSMenu(title: "Murmur")
        menu.delegate = self

        startListeningItem.title = "Start Listening"
        startListeningItem.target = self
        startListeningItem.action = #selector(toggleListening)
        menu.addItem(startListeningItem)

        hotkeyStatusItem.isEnabled = false
        menu.addItem(hotkeyStatusItem)

        permissionItem.target = self
        permissionItem.action = #selector(openKeyboardPermissions)
        menu.addItem(permissionItem)

        menu.addItem(.separator())

        let preferencesItem = NSMenuItem(
            title: "Preferences…",
            action: #selector(openPreferences),
            keyEquivalent: ","
        )
        preferencesItem.target = self
        menu.addItem(preferencesItem)

        menu.addItem(.separator())

        let quitItem = NSMenuItem(
            title: "Quit Murmur",
            action: #selector(quit),
            keyEquivalent: "q"
        )
        quitItem.target = self
        menu.addItem(quitItem)

        return menu
    }

    @objc private func toggleListening() {
        refreshAppContextTooltip()
        audioManager.toggleListening()
        updateMenuState()
    }

    private func showAlert(title: String, message: String) {
        NSApp.activate()

        let alert = NSAlert()
        alert.messageText = title
        alert.informativeText = message
        alert.addButton(withTitle: "OK")
        alert.runModal()
    }

    private func refreshAppContextTooltip() {
        statusItem.button?.toolTip = AppContextDisplayFormatter.tooltip(
            context: appContextDetector.currentContext()
        )
    }

    @objc private func openPreferences() {
        preferencesManager.openPreferences()
    }

    @objc private func quit() {
        NSApp.terminate(nil)
    }

    @objc private func openKeyboardPermissions() {
        guard let url = URL(
            string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
        ) else {
            return
        }

        NSWorkspace.shared.open(url)
    }

    private func startPushToTalk() {
        refreshAppContextTooltip()
        audioManager.startListening()
        updateMenuState()
    }

    private func stopPushToTalk() {
        audioManager.stopListening()
        updateMenuState()
    }

    private func updateMenuState() {
        hotkeyManager?.refreshPermissionStatus()

        startListeningItem.title = audioManager.isListening ? "Stop Listening" : "Start Listening"
        hotkeyStatusItem.title = "Push-to-talk: hold \(hotkeyConfiguration.displayName)"

        if hotkeyManager?.hasRequiredPermissions == true {
            permissionItem.title = "Keyboard access: enabled"
            permissionItem.isEnabled = false
        } else {
            permissionItem.title = "Keyboard access required: open Privacy & Security…"
            permissionItem.isEnabled = true
        }
    }
}

extension MenuBarController: NSMenuDelegate {
    func menuWillOpen(_: NSMenu) {
        updateMenuState()
        refreshAppContextTooltip()
    }
}
