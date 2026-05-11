import MurmurCore
import XCTest

final class LaunchAtLoginStateTests: XCTestCase {
    func testRawExecutableEnvironmentIsUnsupported() {
        let availability = LaunchAtLoginAvailability.evaluate(
            environment: LaunchAtLoginEnvironment(
                bundlePathExtension: "",
                bundleIdentifier: "com.apoorvdayal.murmur"
            )
        )

        XCTAssertEqual(
            availability,
            .unsupported(
                reason: "Requires a signed .app bundle; "
                    + "Swift Package Manager runs as a raw executable."
            )
        )
    }

    func testAppBundleWithoutIdentifierIsUnsupported() {
        let availability = LaunchAtLoginAvailability.evaluate(
            environment: LaunchAtLoginEnvironment(
                bundlePathExtension: "app",
                bundleIdentifier: nil
            )
        )

        XCTAssertEqual(
            availability,
            .unsupported(reason: "Requires an app bundle with CFBundleIdentifier.")
        )
    }

    func testAppBundleWithIdentifierIsAvailable() {
        let availability = LaunchAtLoginAvailability.evaluate(
            environment: LaunchAtLoginEnvironment(
                bundlePathExtension: "app",
                bundleIdentifier: "com.apoorvdayal.murmur"
            )
        )

        XCTAssertEqual(availability, .available)
    }

    func testEnabledStateAllowsDisabling() {
        let state = LaunchAtLoginMenuState.make(
            snapshot: LaunchAtLoginSnapshot(status: .enabled)
        )

        XCTAssertEqual(state.title, "Launch at Login")
        XCTAssertTrue(state.isEnabled)
        XCTAssertTrue(state.isChecked)
        XCTAssertEqual(state.action, .disable)
        XCTAssertNil(state.detail)
    }

    func testDisabledStateAllowsEnabling() {
        let state = LaunchAtLoginMenuState.make(
            snapshot: LaunchAtLoginSnapshot(status: .disabled)
        )

        XCTAssertEqual(state.title, "Launch at Login")
        XCTAssertTrue(state.isEnabled)
        XCTAssertFalse(state.isChecked)
        XCTAssertEqual(state.action, .enable)
    }

    func testRequiresApprovalOpensSystemSettings() {
        let state = LaunchAtLoginMenuState.make(
            snapshot: LaunchAtLoginSnapshot(status: .requiresApproval)
        )

        XCTAssertEqual(state.title, "Approve Launch at Login…")
        XCTAssertTrue(state.isEnabled)
        XCTAssertEqual(state.action, .openSystemSettings)
        XCTAssertEqual(
            state.detail,
            "Enable Murmur in System Settings > General > Login Items."
        )
    }

    func testUnsupportedStateShowsReasonWithoutAction() {
        let state = LaunchAtLoginMenuState.make(
            snapshot: LaunchAtLoginSnapshot(status: .unsupported(reason: "Requires app bundle"))
        )

        XCTAssertEqual(state.title, "Launch at Login Unavailable")
        XCTAssertFalse(state.isEnabled)
        XCTAssertFalse(state.isChecked)
        XCTAssertEqual(state.action, .none)
        XCTAssertEqual(state.detail, "Requires app bundle")
    }
}
