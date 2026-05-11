import Darwin
import Foundation

public struct TranscriptionResponse: Equatable {
    public let text: String
    public let language: String?
    public let speechDetected: Bool
}

public enum DaemonClientError: LocalizedError {
    case invalidPayload(String)
    case invalidResponse(String)
    case daemonUnavailable(String)
    case daemonError(String)

    public var errorDescription: String? {
        switch self {
        case let .invalidPayload(message):
            "Could not encode daemon request: \(message)"
        case let .invalidResponse(message):
            "Daemon returned an invalid response: \(message)"
        case let .daemonUnavailable(message):
            "Murmur daemon is unavailable: \(message)"
        case let .daemonError(message):
            "Murmur daemon error: \(message)"
        }
    }
}

public struct DaemonClient {
    public static let maximumMessageBytes = 10 * 1024 * 1024

    public let socketPath: String
    public let timeoutSeconds: Int

    public init(socketPath: String = DaemonClient.defaultSocketPath(), timeoutSeconds: Int = 2) {
        self.socketPath = socketPath
        self.timeoutSeconds = timeoutSeconds
    }

    public static func defaultSocketPath() -> String {
        FileManager.default.temporaryDirectory.appendingPathComponent("murmur.sock").path
    }

    public func command(_ command: String, payload: [String: Any] = [:]) async throws -> [String: Any] {
        var message = payload
        message["command"] = command
        let frame = try Self.encodeMessage(message)

        return try await Task.detached(priority: .userInitiated) {
            let responseFrame = try Self.send(
                frame: frame,
                socketPath: socketPath,
                timeoutSeconds: timeoutSeconds
            )
            let response = try Self.decodeMessage(responseFrame)
            if let error = response["error"] {
                throw DaemonClientError.daemonError(String(describing: error))
            }
            return response
        }.value
    }

    public func transcribe(
        samples: [Float],
        sampleRate: Int,
        bundleID: String?,
        appName: String?
    ) async throws -> TranscriptionResponse {
        let request = try Self.transcribeRequest(
            samples: samples,
            sampleRate: sampleRate,
            bundleID: bundleID,
            appName: appName
        )
        let response = try await command("transcribe", payload: request)
        return TranscriptionResponse(
            text: response["text"] as? String ?? "",
            language: response["language"] as? String,
            speechDetected: response["speech_detected"] as? Bool ?? true
        )
    }

    public static func transcribeRequest(
        samples: [Float],
        sampleRate: Int,
        bundleID: String? = nil,
        appName: String? = nil,
        language: String? = nil
    ) throws -> [String: Any] {
        guard sampleRate > 0 else {
            throw DaemonClientError.invalidPayload("sample rate must be positive")
        }

        var request: [String: Any] = [
            "command": "transcribe",
            "audio": encodeFloat32Base64(samples),
            "sample_rate": sampleRate
        ]
        if let bundleID, !bundleID.isEmpty {
            request["bundle_id"] = bundleID
        }
        if let appName, !appName.isEmpty {
            request["app_name"] = appName
        }
        if let language, !language.isEmpty {
            request["language"] = language
        }
        return request
    }

    public static func encodeMessage(_ message: [String: Any]) throws -> Data {
        guard JSONSerialization.isValidJSONObject(message) else {
            throw DaemonClientError.invalidPayload("message is not a JSON object")
        }

        let body: Data
        do {
            body = try JSONSerialization.data(withJSONObject: message, options: [])
        } catch {
            throw DaemonClientError.invalidPayload(error.localizedDescription)
        }

        guard body.count <= maximumMessageBytes else {
            throw DaemonClientError.invalidPayload("message exceeds \(maximumMessageBytes) bytes")
        }

        var length = UInt32(body.count).bigEndian
        var frame = Data(bytes: &length, count: MemoryLayout<UInt32>.size)
        frame.append(body)
        return frame
    }

    public static func decodeMessage(_ frame: Data) throws -> [String: Any] {
        guard frame.count >= MemoryLayout<UInt32>.size else {
            throw DaemonClientError.invalidResponse("missing length prefix")
        }

        let declaredLength = frame.prefix(4).reduce(UInt32(0)) { partial, byte in
            (partial << 8) | UInt32(byte)
        }
        guard declaredLength <= maximumMessageBytes else {
            throw DaemonClientError.invalidResponse("message exceeds \(maximumMessageBytes) bytes")
        }
        guard frame.count - 4 == Int(declaredLength) else {
            throw DaemonClientError.invalidResponse(
                "declared \(declaredLength) bytes but received \(frame.count - 4)"
            )
        }

        let body = frame.dropFirst(4)
        let decoded: Any
        do {
            decoded = try JSONSerialization.jsonObject(with: body, options: [])
        } catch {
            throw DaemonClientError.invalidResponse(error.localizedDescription)
        }

        guard let object = decoded as? [String: Any] else {
            throw DaemonClientError.invalidResponse("body is not a JSON object")
        }
        return object
    }

    public static func encodeFloat32Base64(_ samples: [Float]) -> String {
        samples.withUnsafeBufferPointer { buffer in
            Data(buffer: buffer).base64EncodedString()
        }
    }

    private static func send(frame: Data, socketPath: String, timeoutSeconds: Int) throws -> Data {
        let fileDescriptor = Darwin.socket(AF_UNIX, SOCK_STREAM, 0)
        guard fileDescriptor >= 0 else {
            throw DaemonClientError.daemonUnavailable(currentSystemError())
        }
        defer { Darwin.close(fileDescriptor) }
        try configureTimeout(timeoutSeconds, for: fileDescriptor)

        var address = sockaddr_un()
        address.sun_family = sa_family_t(AF_UNIX)
        let maximumPathLength = MemoryLayout.size(ofValue: address.sun_path)
        guard socketPath.utf8.count < maximumPathLength else {
            throw DaemonClientError.daemonUnavailable("socket path is too long: \(socketPath)")
        }

        _ = withUnsafeMutablePointer(to: &address.sun_path) { pointer in
            pointer.withMemoryRebound(to: CChar.self, capacity: maximumPathLength) { rebasedPointer in
                socketPath.withCString { cString in
                    strncpy(rebasedPointer, cString, maximumPathLength - 1)
                }
            }
        }

        let connected = withUnsafePointer(to: &address) { pointer in
            pointer.withMemoryRebound(to: sockaddr.self, capacity: 1) { rebasedPointer in
                Darwin.connect(fileDescriptor, rebasedPointer, socklen_t(MemoryLayout<sockaddr_un>.size))
            }
        }
        guard connected == 0 else {
            throw DaemonClientError.daemonUnavailable("could not connect to \(socketPath): \(currentSystemError())")
        }

        try writeAll(frame, to: fileDescriptor)
        let prefix = try readExactly(byteCount: 4, from: fileDescriptor)
        let responseLength = prefix.reduce(UInt32(0)) { partial, byte in
            (partial << 8) | UInt32(byte)
        }
        guard responseLength <= maximumMessageBytes else {
            throw DaemonClientError.invalidResponse("message exceeds \(maximumMessageBytes) bytes")
        }
        let body = try readExactly(byteCount: Int(responseLength), from: fileDescriptor)
        var responseFrame = prefix
        responseFrame.append(body)
        return responseFrame
    }


    private static func configureTimeout(_ timeoutSeconds: Int, for fileDescriptor: Int32) throws {
        var timeout = timeval(tv_sec: timeoutSeconds, tv_usec: 0)
        let timeoutSize = socklen_t(MemoryLayout<timeval>.size)
        let receiveResult = setsockopt(fileDescriptor, SOL_SOCKET, SO_RCVTIMEO, &timeout, timeoutSize)
        let sendResult = setsockopt(fileDescriptor, SOL_SOCKET, SO_SNDTIMEO, &timeout, timeoutSize)
        guard receiveResult == 0, sendResult == 0 else {
            throw DaemonClientError.daemonUnavailable("could not configure socket timeout: \(currentSystemError())")
        }
    }

    private static func writeAll(_ data: Data, to fileDescriptor: Int32) throws {
        try data.withUnsafeBytes { rawBuffer in
            guard let baseAddress = rawBuffer.baseAddress else {
                return
            }
            var offset = 0
            while offset < data.count {
                let written = Darwin.write(fileDescriptor, baseAddress.advanced(by: offset), data.count - offset)
                guard written > 0 else {
                    throw DaemonClientError.daemonUnavailable("write failed: \(currentSystemError())")
                }
                offset += written
            }
        }
    }

    private static func readExactly(byteCount: Int, from fileDescriptor: Int32) throws -> Data {
        var data = Data(count: byteCount)
        try data.withUnsafeMutableBytes { rawBuffer in
            guard let baseAddress = rawBuffer.baseAddress else {
                return
            }
            var offset = 0
            while offset < byteCount {
                let readCount = Darwin.read(fileDescriptor, baseAddress.advanced(by: offset), byteCount - offset)
                guard readCount > 0 else {
                    throw DaemonClientError.invalidResponse("connection closed before full frame was read")
                }
                offset += readCount
            }
        }
        return data
    }

    private static func currentSystemError() -> String {
        String(cString: strerror(errno))
    }
}
