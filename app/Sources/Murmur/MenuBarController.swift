import AppKit
import MurmurCore

final class MenuBarController: NSObject {
    private let audioManager: AudioCaptureManaging
    private let preferencesManager: PreferencesManaging
    private let appContextDetector: AppContextDetecting
    private let statusItem: NSStatusItem
    private let startListeningItem = NSMenuItem()

    init(
        audioManager: AudioCaptureManaging,
        preferencesManager: PreferencesManaging,
        appContextDetector: AppContextDetecting = AppContextDetector(),
        statusBar: NSStatusBar = .system
    ) {
        self.audioManager = audioManager
        self.preferencesManager = preferencesManager
        self.appContextDetector = appContextDetector
        statusItem = statusBar.statusItem(withLength: NSStatusItem.variableLength)
        super.init()
        configureStatusItem()
    }

    private func configureStatusItem() {
        if let button = statusItem.button {
            button.image = NSImage(systemSymbolName: "waveform", accessibilityDescription: "Murmur")
            button.imagePosition = .imageLeading
            button.toolTip = "Murmur"
        }

        let menu = buildMenu()
        menu.delegate = self
        statusItem.menu = menu
        refreshAppContextTooltip()
    }

    private func buildMenu() -> NSMenu {
        let menu = NSMenu(title: "Murmur")

        startListeningItem.title = "Start Listening"
        startListeningItem.target = self
        startListeningItem.action = #selector(toggleListening)
        menu.addItem(startListeningItem)

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
        startListeningItem.title = audioManager.isListening ? "Stop Listening" : "Start Listening"
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
}

extension MenuBarController: NSMenuDelegate {
    func menuWillOpen(_: NSMenu) {
        refreshAppContextTooltip()
    }
}
