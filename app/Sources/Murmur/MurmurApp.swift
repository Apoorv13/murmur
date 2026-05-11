import AppKit
import MurmurCore

@main
final class MurmurApp: NSObject, NSApplicationDelegate {
    private var menuBarController: MenuBarController?

    func applicationDidFinishLaunching(_: Notification) {
        NSApp.setActivationPolicy(.accessory)
        let launchAtLoginController = LaunchAtLoginController()
        let preferencesManager = AppPreferencesManager(
            launchAtLoginController: launchAtLoginController
        )
        menuBarController = MenuBarController(
            audioManager: AudioCaptureManager(),
            preferencesManager: preferencesManager,
            launchAtLoginController: launchAtLoginController
        )
    }

    func applicationShouldTerminateAfterLastWindowClosed(_: NSApplication) -> Bool {
        false
    }
}
