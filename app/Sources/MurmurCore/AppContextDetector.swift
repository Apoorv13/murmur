import AppKit
import Foundation

public struct AppContext: Codable, Equatable, Sendable {
    public let bundleID: String
    public let appName: String

    public init(bundleID: String, appName: String) {
        self.bundleID = Self.normalized(bundleID)
        self.appName = Self.normalized(appName)
    }

    public var isEmpty: Bool {
        bundleID.isEmpty && appName.isEmpty
    }

    public static func make(bundleID: String?, appName: String?) -> AppContext? {
        let context = AppContext(bundleID: bundleID ?? "", appName: appName ?? "")
        return context.isEmpty ? nil : context
    }

    private static func normalized(_ value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private enum CodingKeys: String, CodingKey {
        case bundleID = "bundle_id"
        case appName = "app_name"
    }
}

public protocol AppContextDetecting {
    func currentContext() -> AppContext?
}

public final class AppContextDetector: AppContextDetecting {
    public init() {}

    public func currentContext() -> AppContext? {
        guard let application = NSWorkspace.shared.frontmostApplication else {
            return nil
        }

        return AppContext.make(
            bundleID: application.bundleIdentifier,
            appName: application.localizedName
        )
    }
}

public enum AppContextDisplayFormatter {
    public static func tooltip(baseTitle: String = "Murmur", context: AppContext?) -> String {
        guard let context else {
            return baseTitle
        }

        let displayName = context.appName.isEmpty ? context.bundleID : context.appName
        guard !displayName.isEmpty else {
            return baseTitle
        }

        return "\(baseTitle) — Active app: \(displayName)"
    }
}
