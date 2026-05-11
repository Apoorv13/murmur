import Foundation
import MurmurCore
import XCTest

final class DaemonClientTests: XCTestCase {
    func testEncodeMessageUsesBigEndianLengthPrefix() throws {
        let frame = try DaemonClient.encodeMessage(["command": "status"])

        let declaredLength = frame.prefix(4).reduce(UInt32(0)) { partial, byte in
            (partial << 8) | UInt32(byte)
        }

        XCTAssertEqual(Int(declaredLength), frame.count - 4)
        let decoded = try DaemonClient.decodeMessage(frame)
        XCTAssertEqual(decoded["command"] as? String, "status")
    }

    func testTranscribeRequestEncodesFloat32AudioAsBase64() throws {
        let samples: [Float] = [0.25, -0.5, 1.0]
        let request = try DaemonClient.transcribeRequest(
            samples: samples,
            sampleRate: 16_000,
            bundleID: "com.example.Editor",
            appName: "Editor"
        )

        XCTAssertEqual(request["command"] as? String, "transcribe")
        XCTAssertEqual(request["sample_rate"] as? Int, 16_000)
        XCTAssertEqual(request["bundle_id"] as? String, "com.example.Editor")
        XCTAssertEqual(request["app_name"] as? String, "Editor")

        let encodedAudio = try XCTUnwrap(request["audio"] as? String)
        let audioData = try XCTUnwrap(Data(base64Encoded: encodedAudio))
        let expectedData = samples.withUnsafeBufferPointer { Data(buffer: $0) }
        XCTAssertEqual(audioData, expectedData)
    }
}
