import Foundation

public struct LaunchAtLoginEnvironment: Equatable, Sendable {
    public let bundlePathExtension: String
    public let bundleIdentifier: String?

    public init(bundlePathExtension: String, bundleIdentifier: String?) {
        self.bundlePathExtension = bundlePathExtension
        self.bundleIdentifier = bundleIdentifier
    }
}

public enum LaunchAtLoginAvailability: Equatable, Sendable {
    case available
    case unsupported(reason: String)

    public static func evaluate(
        environment: LaunchAtLoginEnvironment
    ) -> LaunchAtLoginAvailability {
        guard environment.bundlePathExtension == "app" else {
            return .unsupported(
                reason: "Requires a signed .app bundle; "
                    + "Swift Package Manager runs as a raw executable."
            )
        }

        guard environment.bundleIdentifier?.isEmpty == false else {
            return .unsupported(reason: "Requires an app bundle with CFBundleIdentifier.")
        }

        return .available
    }
}

public enum LaunchAtLoginStatus: Equatable, Sendable {
    case enabled
    case disabled
    case requiresApproval
    case unsupported(reason: String)
    case error(message: String)

    public var isEnabled: Bool {
        if case .enabled = self {
            return true
        }

        return false
    }
}

public struct LaunchAtLoginSnapshot: Equatable, Sendable {
    public let status: LaunchAtLoginStatus

    public init(status: LaunchAtLoginStatus) {
        self.status = status
    }
}

public enum LaunchAtLoginMenuAction: Equatable, Sendable {
    case enable
    case disable
    case openSystemSettings
    case none
}

public struct LaunchAtLoginMenuState: Equatable, Sendable {
    public let title: String
    public let detail: String?
    public let isEnabled: Bool
    public let isChecked: Bool
    public let action: LaunchAtLoginMenuAction

    public init(
        title: String,
        detail: String?,
        isEnabled: Bool,
        isChecked: Bool,
        action: LaunchAtLoginMenuAction
    ) {
        self.title = title
        self.detail = detail
        self.isEnabled = isEnabled
        self.isChecked = isChecked
        self.action = action
    }

    public static func make(snapshot: LaunchAtLoginSnapshot) -> LaunchAtLoginMenuState {
        switch snapshot.status {
        case .enabled:
            return LaunchAtLoginMenuState(
                title: "Launch at Login",
                detail: nil,
                isEnabled: true,
                isChecked: true,
                action: .disable
            )

        case .disabled:
            return LaunchAtLoginMenuState(
                title: "Launch at Login",
                detail: nil,
                isEnabled: true,
                isChecked: false,
                action: .enable
            )

        case .requiresApproval:
            return LaunchAtLoginMenuState(
                title: "Approve Launch at Login…",
                detail: "Enable Murmur in System Settings > General > Login Items.",
                isEnabled: true,
                isChecked: false,
                action: .openSystemSettings
            )

        case let .unsupported(reason):
            return LaunchAtLoginMenuState(
                title: "Launch at Login Unavailable",
                detail: reason,
                isEnabled: false,
                isChecked: false,
                action: .none
            )

        case let .error(message):
            return LaunchAtLoginMenuState(
                title: "Launch at Login Error",
                detail: message,
                isEnabled: false,
                isChecked: false,
                action: .none
            )
        }
    }
}
