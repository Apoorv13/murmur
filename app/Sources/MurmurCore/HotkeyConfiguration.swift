import Foundation

public enum HotkeyEventKind: Equatable, Sendable {
    case keyDown
    case keyUp
    case flagsChanged
}

public enum HotkeyTriggerKind: String, Codable, Equatable, Sendable {
    case key
    case modifier
}

public enum HotkeyActivation: Equatable, Sendable {
    case pressed
    case released
}

public struct HotkeyModifierFlags: OptionSet, Codable, Equatable, Sendable {
    public let rawValue: Int

    public init(rawValue: Int) {
        self.rawValue = rawValue
    }

    public static let shift = HotkeyModifierFlags(rawValue: 1 << 0)
    public static let control = HotkeyModifierFlags(rawValue: 1 << 1)
    public static let option = HotkeyModifierFlags(rawValue: 1 << 2)
    public static let command = HotkeyModifierFlags(rawValue: 1 << 3)
    public static let function = HotkeyModifierFlags(rawValue: 1 << 4)
}

public struct HotkeyEvent: Equatable, Sendable {
    public let kind: HotkeyEventKind
    public let keyCode: UInt16
    public let modifierFlags: HotkeyModifierFlags
    public let isRepeat: Bool

    public init(
        kind: HotkeyEventKind,
        keyCode: UInt16,
        modifierFlags: HotkeyModifierFlags = [],
        isRepeat: Bool = false
    ) {
        self.kind = kind
        self.keyCode = keyCode
        self.modifierFlags = modifierFlags
        self.isRepeat = isRepeat
    }
}

public struct HotkeyConfiguration: Codable, Equatable, Sendable {
    public let keyCode: UInt16
    public let triggerKind: HotkeyTriggerKind
    public let requiredModifiers: HotkeyModifierFlags
    public let displayName: String

    public init(
        keyCode: UInt16,
        triggerKind: HotkeyTriggerKind,
        requiredModifiers: HotkeyModifierFlags = [],
        displayName: String
    ) {
        self.keyCode = keyCode
        self.triggerKind = triggerKind
        self.requiredModifiers = requiredModifiers
        self.displayName = displayName
    }

    public static let rightOption = HotkeyConfiguration(
        keyCode: 61,
        triggerKind: .modifier,
        requiredModifiers: .option,
        displayName: "Right Option"
    )
}

public struct HotkeyMatcher: Equatable, Sendable {
    public private(set) var isPressed: Bool

    public init(isPressed: Bool = false) {
        self.isPressed = isPressed
    }

    public mutating func activation(
        for event: HotkeyEvent,
        configuration: HotkeyConfiguration
    ) -> HotkeyActivation? {
        guard event.keyCode == configuration.keyCode else {
            return nil
        }

        switch configuration.triggerKind {
        case .modifier:
            guard event.kind == .flagsChanged else {
                return nil
            }

            let requiredModifierStillDown = event.modifierFlags
                .isSuperset(of: configuration.requiredModifiers)
            let pressed = requiredModifierStillDown ? !isPressed : false
            return transition(to: pressed)

        case .key:
            switch event.kind {
            case .keyDown:
                guard !event.isRepeat,
                      event.modifierFlags.isSuperset(of: configuration.requiredModifiers) else {
                    return nil
                }

                return transition(to: true)

            case .keyUp:
                return transition(to: false)

            case .flagsChanged:
                return nil
            }
        }
    }

    private mutating func transition(to pressed: Bool) -> HotkeyActivation? {
        guard pressed != isPressed else {
            return nil
        }

        isPressed = pressed
        return pressed ? .pressed : .released
    }
}

public final class UserDefaultsHotkeyConfigurationStore {
    public enum Keys {
        public static let keyCode = "PushToTalkHotkeyKeyCode"
        public static let triggerKind = "PushToTalkHotkeyTriggerKind"
        public static let requiredModifiers = "PushToTalkHotkeyRequiredModifiers"
        public static let displayName = "PushToTalkHotkeyDisplayName"
    }

    private let defaults: UserDefaults

    public init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
    }

    public func loadPushToTalkHotkey() -> HotkeyConfiguration {
        let fallback = HotkeyConfiguration.rightOption

        guard defaults.object(forKey: Keys.keyCode) != nil else {
            return fallback
        }

        let keyCode = UInt16(clamping: defaults.integer(forKey: Keys.keyCode))
        let triggerKind = defaults
            .string(forKey: Keys.triggerKind)
            .flatMap(HotkeyTriggerKind.init(rawValue:)) ?? fallback.triggerKind
        let requiredModifiersRaw = defaults.object(forKey: Keys.requiredModifiers) == nil
            ? fallback.requiredModifiers.rawValue
            : defaults.integer(forKey: Keys.requiredModifiers)
        let displayName = defaults.string(forKey: Keys.displayName) ?? fallback.displayName

        return HotkeyConfiguration(
            keyCode: keyCode,
            triggerKind: triggerKind,
            requiredModifiers: HotkeyModifierFlags(rawValue: requiredModifiersRaw),
            displayName: displayName
        )
    }

    public func savePushToTalkHotkey(_ configuration: HotkeyConfiguration) {
        defaults.set(Int(configuration.keyCode), forKey: Keys.keyCode)
        defaults.set(configuration.triggerKind.rawValue, forKey: Keys.triggerKind)
        defaults.set(configuration.requiredModifiers.rawValue, forKey: Keys.requiredModifiers)
        defaults.set(configuration.displayName, forKey: Keys.displayName)
    }
}
