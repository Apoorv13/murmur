import Foundation
import MurmurCore
import ServiceManagement

protocol LaunchAtLoginControlling: AnyObject {
    func currentSnapshot() -> LaunchAtLoginSnapshot
    func setEnabled(_ enabled: Bool) -> LaunchAtLoginSnapshot
}

final class LaunchAtLoginController: LaunchAtLoginControlling {
    private let bundle: Bundle
    private let service: SMAppService

    init(bundle: Bundle = .main, service: SMAppService = .mainApp) {
        self.bundle = bundle
        self.service = service
    }

    func currentSnapshot() -> LaunchAtLoginSnapshot {
        guard let unsupportedReason = unsupportedReason() else {
            return LaunchAtLoginSnapshot(status: map(service.status))
        }

        return LaunchAtLoginSnapshot(status: .unsupported(reason: unsupportedReason))
    }

    func setEnabled(_ enabled: Bool) -> LaunchAtLoginSnapshot {
        guard unsupportedReason() == nil else {
            return currentSnapshot()
        }

        do {
            if enabled {
                try service.register()
            } else {
                try service.unregister()
            }

            return currentSnapshot()
        } catch {
            return LaunchAtLoginSnapshot(status: .error(message: error.localizedDescription))
        }
    }

    private func unsupportedReason() -> String? {
        let environment = LaunchAtLoginEnvironment(
            bundlePathExtension: bundle.bundleURL.pathExtension,
            bundleIdentifier: bundle.bundleIdentifier
        )

        switch LaunchAtLoginAvailability.evaluate(environment: environment) {
        case .available:
            return nil
        case let .unsupported(reason):
            return reason
        }
    }

    private func map(_ status: SMAppService.Status) -> LaunchAtLoginStatus {
        switch status {
        case .enabled:
            return .enabled
        case .requiresApproval:
            return .requiresApproval
        case .notRegistered:
            return .disabled
        case .notFound:
            return .unsupported(reason: "Login item registration was not found for this app bundle.")
        @unknown default:
            return .error(message: "Unknown launch-at-login status.")
        }
    }
}
