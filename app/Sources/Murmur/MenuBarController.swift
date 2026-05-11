import AppKit
import MurmurCore

final class MenuBarController: NSObject {
    private let audioManager: AudioCaptureManaging
    private let preferencesManager: PreferencesManaging
    private let appContextDetector: AppContextDetecting
    private let hotkeyConfiguration: HotkeyConfiguration
    private let statusItem: NSStatusItem
    private let currentStatusItem = NSMenuItem()
    private let startListeningItem = NSMenuItem()
    private let hotkeyStatusItem = NSMenuItem()
    private let permissionItem = NSMenuItem()
    private var hotkeyManager: HotkeyManager?
    private var statusState: MenuBarStatusState = .idle

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
            button.imagePosition = .imageLeading
        }

        statusItem.menu = buildMenu()
        updateMenuState()
    }

    private func configureAudioManagerCallbacks() {
        audioManager.onStateChanged = { [weak self] _ in
            self?.updateMenuState()
        }
        audioManager.onError = { [weak self] message in
            self?.updateStatus(.error)
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

        currentStatusItem.isEnabled = false
        menu.addItem(currentStatusItem)
        menu.addItem(.separator())

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

    func updateStatus(_ state: MenuBarStatusState) {
        statusState = state
        let rendering = MenuBarStatusRenderer.render(state)

        if let button = statusItem.button {
            button.image = NSImage(
                systemSymbolName: rendering.systemSymbolName,
                accessibilityDescription: rendering.accessibilityDescription
            )
            button.title = rendering.title
            button.contentTintColor = tintColor(for: state)
        }

        currentStatusItem.title = rendering.statusMenuTitle
        startListeningItem.title = rendering.toggleMenuTitle
        refreshAppContextTooltip()
    }

    private func refreshAppContextTooltip() {
        let rendering = MenuBarStatusRenderer.render(statusState)
        statusItem.button?.toolTip = AppContextDisplayFormatter.tooltip(
            baseTitle: rendering.tooltipTitle,
            context: appContextDetector.currentContext()
        )
    }

    private func tintColor(for state: MenuBarStatusState) -> NSColor? {
        switch state {
        case .idle:
            return nil
        case .listening:
            return .systemRed
        case .processing:
            return .systemBlue
        case .error:
            return .systemOrange
        }
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
        audioManager.startListening()
        updateMenuState()
    }

    private func stopPushToTalk() {
        audioManager.stopListening()
        updateMenuState()
    }

    private func updateMenuState() {
        hotkeyManager?.refreshPermissionStatus()

        updateStatus(audioManager.status)
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
    }
}
