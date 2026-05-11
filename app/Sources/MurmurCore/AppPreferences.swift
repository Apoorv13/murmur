import Foundation

public enum PushToTalkHotkeyPreset: String, CaseIterable, Codable, Equatable, Hashable, Sendable {
    case rightOption = "rightOption"
    case commandSpace = "commandSpace"

    public var displayName: String {
        switch self {
        case .rightOption:
            "Right Option"
        case .commandSpace:
            "Command-Space"
        }
    }

    public var configuration: HotkeyConfiguration {
        switch self {
        case .rightOption:
            .rightOption
        case .commandSpace:
            HotkeyConfiguration(
                keyCode: 49,
                triggerKind: .key,
                requiredModifiers: .command,
                displayName: displayName
            )
        }
    }

    public static func matching(_ configuration: HotkeyConfiguration) -> PushToTalkHotkeyPreset? {
        allCases.first { $0.configuration == configuration }
    }
}

public enum TranscriptionModelSelection: String, CaseIterable, Codable, Equatable, Hashable, Sendable {
    case whisperTiny = "whisper-tiny"
    case whisperBase = "whisper-base"
    case whisperSmall = "whisper-small"
    case parakeetV2 = "parakeet-tdt-0.6b-v2"
    case parakeetV3 = "parakeet-tdt-0.6b-v3"

    public var displayName: String {
        switch self {
        case .whisperTiny:
            "Whisper Tiny"
        case .whisperBase:
            "Whisper Base"
        case .whisperSmall:
            "Whisper Small"
        case .parakeetV2:
            "Parakeet TDT 0.6B v2"
        case .parakeetV3:
            "Parakeet TDT 0.6B v3"
        }
    }
}

public enum LanguageAccentProfile: String, CaseIterable, Codable, Equatable, Hashable, Sendable {
    case automatic
    case englishUS = "english-us"
    case englishUK = "english-uk"
    case englishAU = "english-au"
    case englishIN = "english-in"

    public var displayName: String {
        switch self {
        case .automatic:
            "Automatic"
        case .englishUS:
            "English (US)"
        case .englishUK:
            "English (UK)"
        case .englishAU:
            "English (Australia)"
        case .englishIN:
            "English (India)"
        }
    }
}

public struct AppPreferences: Codable, Equatable, Sendable {
    public static let defaultHotkeyPreset: PushToTalkHotkeyPreset = .rightOption
    public static let defaultModel: TranscriptionModelSelection = .whisperBase
    public static let defaultLanguageAccent: LanguageAccentProfile = .automatic
    public static let defaultIdleTimeoutSeconds = 300
    public static let minimumIdleTimeoutSeconds = 30
    public static let maximumIdleTimeoutSeconds = 3_600

    public var hotkeyPreset: PushToTalkHotkeyPreset
    public var pushToTalkHotkey: HotkeyConfiguration
    public var selectedModel: TranscriptionModelSelection
    public var languageAccentProfile: LanguageAccentProfile
    public var idleTimeoutSeconds: Int
    public var launchAtLogin: Bool

    public init(
        hotkeyPreset: PushToTalkHotkeyPreset = defaultHotkeyPreset,
        pushToTalkHotkey: HotkeyConfiguration = defaultHotkeyPreset.configuration,
        selectedModel: TranscriptionModelSelection = defaultModel,
        languageAccentProfile: LanguageAccentProfile = defaultLanguageAccent,
        idleTimeoutSeconds: Int = defaultIdleTimeoutSeconds,
        launchAtLogin: Bool = false
    ) {
        self.hotkeyPreset = hotkeyPreset
        self.pushToTalkHotkey = pushToTalkHotkey
        self.selectedModel = selectedModel
        self.languageAccentProfile = languageAccentProfile
        self.idleTimeoutSeconds = Self.clampedIdleTimeout(idleTimeoutSeconds)
        self.launchAtLogin = launchAtLogin
    }

    public static var defaults: AppPreferences {
        AppPreferences()
    }

    public static func clampedIdleTimeout(_ seconds: Int) -> Int {
        min(max(seconds, minimumIdleTimeoutSeconds), maximumIdleTimeoutSeconds)
    }
}

public final class UserDefaultsAppPreferencesStore {
    public enum Keys {
        public static let hotkeyPreset = "PushToTalkHotkeyPreset"
        public static let selectedModel = "SelectedTranscriptionModel"
        public static let languageAccentProfile = "LanguageAccentProfile"
        public static let idleTimeoutSeconds = "IdleTimeoutSeconds"
        public static let launchAtLogin = "LaunchAtLogin"
    }

    private let defaults: UserDefaults
    private let hotkeyStore: UserDefaultsHotkeyConfigurationStore

    public init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        hotkeyStore = UserDefaultsHotkeyConfigurationStore(defaults: defaults)
    }

    public func load() -> AppPreferences {
        let hotkey = hotkeyStore.loadPushToTalkHotkey()
        let preset = defaults
            .string(forKey: Keys.hotkeyPreset)
            .flatMap(PushToTalkHotkeyPreset.init(rawValue:))
            ?? PushToTalkHotkeyPreset.matching(hotkey)
            ?? AppPreferences.defaultHotkeyPreset
        let idleTimeout = defaults.object(forKey: Keys.idleTimeoutSeconds) == nil
            ? AppPreferences.defaultIdleTimeoutSeconds
            : defaults.integer(forKey: Keys.idleTimeoutSeconds)

        return AppPreferences(
            hotkeyPreset: preset,
            pushToTalkHotkey: hotkey,
            selectedModel: defaults
                .string(forKey: Keys.selectedModel)
                .flatMap(TranscriptionModelSelection.init(rawValue:))
                ?? AppPreferences.defaultModel,
            languageAccentProfile: defaults
                .string(forKey: Keys.languageAccentProfile)
                .flatMap(LanguageAccentProfile.init(rawValue:))
                ?? AppPreferences.defaultLanguageAccent,
            idleTimeoutSeconds: idleTimeout,
            launchAtLogin: defaults.bool(forKey: Keys.launchAtLogin)
        )
    }

    public func save(_ preferences: AppPreferences) {
        let normalized = AppPreferences(
            hotkeyPreset: preferences.hotkeyPreset,
            pushToTalkHotkey: preferences.pushToTalkHotkey,
            selectedModel: preferences.selectedModel,
            languageAccentProfile: preferences.languageAccentProfile,
            idleTimeoutSeconds: preferences.idleTimeoutSeconds,
            launchAtLogin: preferences.launchAtLogin
        )

        defaults.set(normalized.hotkeyPreset.rawValue, forKey: Keys.hotkeyPreset)
        defaults.set(normalized.selectedModel.rawValue, forKey: Keys.selectedModel)
        defaults.set(normalized.languageAccentProfile.rawValue, forKey: Keys.languageAccentProfile)
        defaults.set(normalized.idleTimeoutSeconds, forKey: Keys.idleTimeoutSeconds)
        defaults.set(normalized.launchAtLogin, forKey: Keys.launchAtLogin)
        hotkeyStore.savePushToTalkHotkey(normalized.pushToTalkHotkey)
    }
}
