import AppKit
import MurmurCore
import SwiftUI

final class PreferencesWindowController: NSWindowController {
    init(viewModel: PreferencesViewModel) {
        let hostingController = NSHostingController(
            rootView: PreferencesView(viewModel: viewModel)
        )
        let window = NSWindow(contentViewController: hostingController)
        window.title = "Murmur Preferences"
        window.styleMask = [.titled, .closable, .miniaturizable]
        window.isReleasedWhenClosed = false
        window.setContentSize(NSSize(width: 520, height: 430))
        window.center()

        super.init(window: window)
    }

    @available(*, unavailable)
    required init?(coder _: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }
}

final class PreferencesViewModel: ObservableObject {
    @Published var hotkeyPreset: PushToTalkHotkeyPreset {
        didSet {
            preferences.hotkeyPreset = hotkeyPreset
            preferences.pushToTalkHotkey = hotkeyPreset.configuration
            savePreferences()
        }
    }

    @Published var selectedModel: TranscriptionModelSelection {
        didSet {
            preferences.selectedModel = selectedModel
            savePreferences()
        }
    }

    @Published var languageAccentProfile: LanguageAccentProfile {
        didSet {
            preferences.languageAccentProfile = languageAccentProfile
            savePreferences()
        }
    }

    @Published var idleTimeoutSeconds: Int {
        didSet {
            preferences.idleTimeoutSeconds = AppPreferences
                .clampedIdleTimeout(idleTimeoutSeconds)
            idleTimeoutSeconds = preferences.idleTimeoutSeconds
            savePreferences()
        }
    }

    @Published var launchAtLogin: Bool {
        didSet {
            preferences.launchAtLogin = launchAtLogin
            savePreferences()
            applyLaunchAtLoginPreference()
        }
    }

    @Published private(set) var launchAtLoginStatus: String

    var currentHotkeyDisplayName: String {
        preferences.pushToTalkHotkey.displayName
    }

    var onPreferencesChanged: ((AppPreferences) -> Void)?

    private var preferences: AppPreferences
    private let store: UserDefaultsAppPreferencesStore
    private let launchAtLoginController: LaunchAtLoginControlling

    init(
        preferences: AppPreferences,
        store: UserDefaultsAppPreferencesStore,
        launchAtLoginController: LaunchAtLoginControlling
    ) {
        self.preferences = preferences
        self.store = store
        self.launchAtLoginController = launchAtLoginController
        let launchAtLoginSnapshot = launchAtLoginController.currentSnapshot()
        hotkeyPreset = preferences.hotkeyPreset
        selectedModel = preferences.selectedModel
        languageAccentProfile = preferences.languageAccentProfile
        idleTimeoutSeconds = preferences.idleTimeoutSeconds
        launchAtLogin = launchAtLoginSnapshot.status.isEnabled || preferences.launchAtLogin
        launchAtLoginStatus = Self.statusText(for: launchAtLoginSnapshot)
    }

    private func savePreferences() {
        store.save(preferences)
        onPreferencesChanged?(preferences)
    }

    private func applyLaunchAtLoginPreference() {
        let snapshot = launchAtLoginController.setEnabled(launchAtLogin)
        launchAtLoginStatus = Self.statusText(for: snapshot)
    }

    private static func statusText(for snapshot: LaunchAtLoginSnapshot) -> String {
        switch snapshot.status {
        case .enabled:
            "Launch at login is enabled."
        case .disabled:
            "Launch at login uses macOS Login Items."
        case .requiresApproval:
            "Approve Murmur in System Settings > General > Login Items."
        case let .unsupported(reason):
            "Saved locally; \(reason)"
        case let .error(message):
            "Saved locally; \(message)"
        }
    }
}

struct PreferencesView: View {
    @ObservedObject var viewModel: PreferencesViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            GroupBox("Push-to-talk") {
                VStack(alignment: .leading, spacing: 8) {
                    Picker("Hotkey", selection: $viewModel.hotkeyPreset) {
                        ForEach(PushToTalkHotkeyPreset.allCases, id: \.self) { preset in
                            Text(preset.displayName).tag(preset)
                        }
                    }
                    Text("Current: hold \(viewModel.currentHotkeyDisplayName)")
                        .foregroundStyle(.secondary)
                    Text("Changes apply immediately to the menu bar listener.")
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }

            GroupBox("Transcription") {
                VStack(alignment: .leading, spacing: 10) {
                    Picker("Model", selection: $viewModel.selectedModel) {
                        ForEach(TranscriptionModelSelection.allCases, id: \.self) { model in
                            Text(model.displayName).tag(model)
                        }
                    }

                    Picker("Language/accent", selection: $viewModel.languageAccentProfile) {
                        ForEach(LanguageAccentProfile.allCases, id: \.self) { profile in
                            Text(profile.displayName).tag(profile)
                        }
                    }

                    Stepper(
                        "Idle timeout: \(viewModel.idleTimeoutSeconds) seconds",
                        value: $viewModel.idleTimeoutSeconds,
                        in: AppPreferences.minimumIdleTimeoutSeconds...AppPreferences
                            .maximumIdleTimeoutSeconds,
                        step: 30
                    )
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }

            GroupBox("Startup") {
                VStack(alignment: .leading, spacing: 8) {
                    Toggle("Launch Murmur at login", isOn: $viewModel.launchAtLogin)
                    Text(viewModel.launchAtLoginStatus)
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }

            Spacer()
        }
        .padding(20)
        .frame(width: 520, height: 430, alignment: .topLeading)
    }
}
