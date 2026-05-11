import Foundation
import MurmurCore

func require(_ condition: @autoclosure () -> Bool, _ message: String) throws {
    if !condition() {
        throw CheckFailure(message)
    }
}

struct CheckFailure: Error, CustomStringConvertible {
    let description: String

    init(_ description: String) {
        self.description = description
    }
}

let frame = try DaemonClient.encodeMessage(["command": "status"])
let declaredLength = frame.prefix(4).reduce(UInt32(0)) { partial, byte in
    (partial << 8) | UInt32(byte)
}
try require(Int(declaredLength) == frame.count - 4, "length prefix does not match JSON body size")
let decoded = try DaemonClient.decodeMessage(frame)
try require(decoded["command"] as? String == "status", "decoded command mismatch")

let samples: [Float] = [0.25, -0.5, 1.0]
let request = try DaemonClient.transcribeRequest(
    samples: samples,
    sampleRate: 16_000,
    bundleID: "com.example.Editor",
    appName: "Editor"
)
try require(request["command"] as? String == "transcribe", "transcribe command missing")
try require(request["sample_rate"] as? Int == 16_000, "sample rate missing")
try require(request["bundle_id"] as? String == "com.example.Editor", "bundle ID missing")
try require(request["app_name"] as? String == "Editor", "app name missing")

let encodedAudio = request["audio"] as? String
try require(encodedAudio != nil, "audio payload missing")
let audioData = Data(base64Encoded: encodedAudio ?? "")
let expectedData = samples.withUnsafeBufferPointer { Data(buffer: $0) }
try require(audioData == expectedData, "audio payload is not native float32 bytes")

print("IPC framing checks passed")
