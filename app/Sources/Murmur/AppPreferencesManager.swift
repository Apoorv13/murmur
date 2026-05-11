import AppKit
import MurmurCore

final class AppPreferencesManager: PreferencesManaging {
    var onPreferencesChanged: ((AppPreferences) -> Void)?

    private let store: UserDefaultsAppPreferencesStore
    private let launchAtLoginController: LaunchAtLoginControlling
    private var windowController: PreferencesWindowController?

    init(
        store: UserDefaultsAppPreferencesStore = UserDefaultsAppPreferencesStore(),
        launchAtLoginController: LaunchAtLoginControlling = LaunchAtLoginController()
    ) {
        self.store = store
        self.launchAtLoginController = launchAtLoginController
    }

    func openPreferences() {
        let controller = windowController ?? makeWindowController()
        windowController = controller
        controller.showWindow(nil)
        controller.window?.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    private func makeWindowController() -> PreferencesWindowController {
        let viewModel = PreferencesViewModel(
            preferences: store.load(),
            store: store,
            launchAtLoginController: launchAtLoginController
        )
        viewModel.onPreferencesChanged = { [weak self] preferences in
            self?.onPreferencesChanged?(preferences)
        }

        return PreferencesWindowController(viewModel: viewModel)
    }
}
