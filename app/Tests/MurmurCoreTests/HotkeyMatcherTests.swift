import MurmurCore
import XCTest

final class HotkeyMatcherTests: XCTestCase {
    func testRightOptionPressAndRelease() {
        var matcher = HotkeyMatcher()

        let press = HotkeyEvent(
            kind: .flagsChanged,
            keyCode: 61,
            modifierFlags: .option
        )
        let release = HotkeyEvent(
            kind: .flagsChanged,
            keyCode: 61,
            modifierFlags: []
        )

        XCTAssertEqual(
            matcher.activation(for: press, configuration: .rightOption),
            .pressed
        )
        XCTAssertEqual(
            matcher.activation(for: release, configuration: .rightOption),
            .released
        )
    }

    func testLeftOptionDoesNotMatchRightOption() {
        var matcher = HotkeyMatcher()
        let leftOptionPress = HotkeyEvent(
            kind: .flagsChanged,
            keyCode: 58,
            modifierFlags: .option
        )

        XCTAssertNil(matcher.activation(for: leftOptionPress, configuration: .rightOption))
    }

    func testRightOptionReleaseMatchesWhenLeftOptionRemainsHeld() {
        var matcher = HotkeyMatcher()
        let press = HotkeyEvent(
            kind: .flagsChanged,
            keyCode: 61,
            modifierFlags: .option
        )

        XCTAssertEqual(
            matcher.activation(for: press, configuration: .rightOption),
            .pressed
        )
        XCTAssertEqual(
            matcher.activation(for: press, configuration: .rightOption),
            .released
        )
    }

    func testKeyHotkeyRequiresModifiersAndIgnoresRepeats() {
        let commandSpace = HotkeyConfiguration(
            keyCode: 49,
            triggerKind: .key,
            requiredModifiers: .command,
            displayName: "Command-Space"
        )
        var matcher = HotkeyMatcher()

        XCTAssertNil(
            matcher.activation(
                for: HotkeyEvent(kind: .keyDown, keyCode: 49),
                configuration: commandSpace
            )
        )
        XCTAssertEqual(
            matcher.activation(
                for: HotkeyEvent(kind: .keyDown, keyCode: 49, modifierFlags: .command),
                configuration: commandSpace
            ),
            .pressed
        )
        XCTAssertNil(
            matcher.activation(
                for: HotkeyEvent(
                    kind: .keyDown,
                    keyCode: 49,
                    modifierFlags: .command,
                    isRepeat: true
                ),
                configuration: commandSpace
            )
        )
        XCTAssertEqual(
            matcher.activation(
                for: HotkeyEvent(kind: .keyUp, keyCode: 49),
                configuration: commandSpace
            ),
            .released
        )
    }
}
