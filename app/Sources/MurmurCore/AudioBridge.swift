import AppKit
import AVFoundation
import Foundation

public struct AudioCaptureResult {
    public let samples: [Float]
    public let sampleRate: Int
}

public enum AudioBridgeError: LocalizedError {
    case microphoneDenied
    case microphoneRestricted
    case inputUnavailable
    case alreadyCapturing
    case notCapturing
    case noAudioCaptured
    case unsupportedAudioFormat

    public var errorDescription: String? {
        switch self {
        case .microphoneDenied:
            "Microphone access is denied. Enable it in System Settings > Privacy & Security > Microphone."
        case .microphoneRestricted:
            "Microphone access is restricted on this Mac."
        case .inputUnavailable:
            "No microphone input is available."
        case .alreadyCapturing:
            "Audio capture is already running."
        case .notCapturing:
            "Audio capture is not running."
        case .noAudioCaptured:
            "No microphone audio was captured."
        case .unsupportedAudioFormat:
            "The microphone produced an unsupported audio format."
        }
    }
}

public final class AudioBridge {
    private let daemonClient: DaemonClient
    private let engine = AVAudioEngine()
    private let sampleQueue = DispatchQueue(label: "dev.murmur.audio.samples")
    private var samples: [Float] = []
    private var captureError: AudioBridgeError?
    private var sampleRate = 16_000

    public private(set) var isCapturing = false

    public init(daemonClient: DaemonClient = DaemonClient()) {
        self.daemonClient = daemonClient
    }

    public func startCapture() async throws {
        try await requestMicrophonePermission()
        try startEngine()
    }

    public func stopAndTranscribe(bundleID: String?, appName: String?) async throws -> TranscriptionResponse {
        let capturedAudio = try stopCapture()
        return try await daemonClient.transcribe(
            samples: capturedAudio.samples,
            sampleRate: capturedAudio.sampleRate,
            bundleID: bundleID,
            appName: appName
        )
    }

    public func stopCapture() throws -> AudioCaptureResult {
        guard isCapturing else {
            throw AudioBridgeError.notCapturing
        }

        engine.inputNode.removeTap(onBus: 0)
        engine.stop()
        isCapturing = false

        let capture = sampleQueue.sync { () -> (samples: [Float], error: AudioBridgeError?) in
            let capture = (samples, captureError)
            samples = []
            captureError = nil
            return capture
        }

        if let error = capture.error {
            throw error
        }
        guard !capture.samples.isEmpty else {
            throw AudioBridgeError.noAudioCaptured
        }
        return AudioCaptureResult(samples: capture.samples, sampleRate: sampleRate)
    }

    private func requestMicrophonePermission() async throws {
        switch AVCaptureDevice.authorizationStatus(for: .audio) {
        case .authorized:
            return
        case .denied:
            throw AudioBridgeError.microphoneDenied
        case .restricted:
            throw AudioBridgeError.microphoneRestricted
        case .notDetermined:
            let granted = await AVCaptureDevice.requestAccess(for: .audio)
            if !granted {
                throw AudioBridgeError.microphoneDenied
            }
        @unknown default:
            throw AudioBridgeError.microphoneRestricted
        }
    }

    private func startEngine() throws {
        guard !isCapturing else {
            throw AudioBridgeError.alreadyCapturing
        }

        let inputNode = engine.inputNode
        let format = inputNode.outputFormat(forBus: 0)
        guard format.channelCount > 0, format.sampleRate > 0 else {
            throw AudioBridgeError.inputUnavailable
        }

        sampleRate = Int(format.sampleRate.rounded())
        sampleQueue.sync {
            samples = []
            captureError = nil
        }

        inputNode.installTap(onBus: 0, bufferSize: 4_096, format: format) { [weak self] buffer, _ in
            self?.append(buffer: buffer)
        }

        do {
            engine.prepare()
            try engine.start()
            isCapturing = true
        } catch {
            inputNode.removeTap(onBus: 0)
            throw error
        }
    }

    private func append(buffer: AVAudioPCMBuffer) {
        guard let channelData = buffer.floatChannelData else {
            sampleQueue.async { [weak self] in
                self?.captureError = .unsupportedAudioFormat
            }
            return
        }

        let channelCount = Int(buffer.format.channelCount)
        let frameCount = Int(buffer.frameLength)
        guard channelCount > 0, frameCount > 0 else {
            return
        }

        var chunk = [Float](repeating: 0, count: frameCount)
        if channelCount == 1 {
            let monoChannel = UnsafeBufferPointer(start: channelData[0], count: frameCount)
            chunk = Array(monoChannel)
        } else {
            for channelIndex in 0..<channelCount {
                let channel = UnsafeBufferPointer(start: channelData[channelIndex], count: frameCount)
                for frameIndex in 0..<frameCount {
                    chunk[frameIndex] += channel[frameIndex] / Float(channelCount)
                }
            }
        }

        sampleQueue.async { [weak self] in
            self?.samples.append(contentsOf: chunk)
        }
    }
}
