import AppKit

@main
final class MurmurApp: NSObject, NSApplicationDelegate {
    private var menuBarController: MenuBarController?

    func applicationDidFinishLaunching(_: Notification) {
        NSApp.setActivationPolicy(.accessory)
        menuBarController = MenuBarController(
            audioManager: AudioCaptureManager(),
            preferencesManager: PreferencesManager()
        )
    }

    func applicationShouldTerminateAfterLastWindowClosed(_: NSApplication) -> Bool {
        false
    }
}
