import MurmurCore
import XCTest

final class AppPreferencesStoreTests: XCTestCase {
    func testLoadReturnsDefaultsWhenNoValuesAreStored() {
        let store = makeStore()

        XCTAssertEqual(store.load(), .defaults)
    }

    func testSavePersistsPreferences() {
        let defaults = makeDefaults()
        let store = UserDefaultsAppPreferencesStore(defaults: defaults)
        let preferences = AppPreferences(
            hotkeyPreset: .commandSpace,
            pushToTalkHotkey: PushToTalkHotkeyPreset.commandSpace.configuration,
            selectedModel: .parakeetV3,
            languageAccentProfile: .englishIN,
            idleTimeoutSeconds: 900,
            launchAtLogin: true
        )

        store.save(preferences)

        XCTAssertEqual(UserDefaultsAppPreferencesStore(defaults: defaults).load(), preferences)
    }

    func testIdleTimeoutIsClampedWhenLoaded() {
        let defaults = makeDefaults()
        defaults.set(1, forKey: UserDefaultsAppPreferencesStore.Keys.idleTimeoutSeconds)

        XCTAssertEqual(
            UserDefaultsAppPreferencesStore(defaults: defaults).load().idleTimeoutSeconds,
            AppPreferences.minimumIdleTimeoutSeconds
        )
    }

    private func makeStore() -> UserDefaultsAppPreferencesStore {
        UserDefaultsAppPreferencesStore(defaults: makeDefaults())
    }

    private func makeDefaults() -> UserDefaults {
        let suiteName = "MurmurTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        return defaults
    }
}
