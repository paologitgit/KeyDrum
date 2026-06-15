import AVFoundation

enum LooperState {
    case empty, recording, playing, overdubbing, stopped
}

enum LengthMultiplier: Int, CaseIterable, Identifiable {
    case one = 1, two = 2, four = 4, eight = 8
    var id: Int { rawValue }
    var label: String {
        switch self {
        case .one: return "1×"
        case .two: return "2×"
        case .four: return "4×"
        case .eight: return "8×"
        }
    }
}

@MainActor
class LooperTrack: ObservableObject {
    let id: Int
    @Published var state: LooperState = .empty
    @Published var multiplier: LengthMultiplier = .one
    @Published var volume: Float = 0.8
    @Published var isMuted: Bool = false

    private let playerNode = AVAudioPlayerNode()
    private var loopBuffer: AVAudioPCMBuffer?
    // accumulates raw input during recording
    private var captureBuffer: [Float] = []
    private var capturedFrames: Int = 0
    private var loopLengthSamples: Int = 0
    private var sampleRate: Double = 44100

    let engine: AVAudioEngine
    let mixer: AVAudioMixerNode

    init(id: Int, engine: AVAudioEngine, mixer: AVAudioMixerNode) {
        self.id = id
        self.engine = engine
        self.mixer = mixer
        engine.attach(playerNode)
        engine.connect(playerNode, to: mixer, format: nil)
    }

    func configure(sampleRate: Double) {
        self.sampleRate = sampleRate
    }

    // Called from audio thread — must be non-isolated
    nonisolated func feedInput(_ samples: UnsafePointer<Float>, count: Int) {
        // Read state without main actor — use a simple flag
        // We store a nonisolated mirror of the state
        guard _isCapturing else { return }

        let remaining = _loopLengthSamples - _capturedFrames
        guard remaining > 0 else { return }

        let toCopy = min(count, remaining)
        let dst = UnsafeMutablePointer<Float>(&_captureData[_capturedFrames])
        dst.initialize(from: samples, count: toCopy)
        _capturedFrames += toCopy

        if _capturedFrames >= _loopLengthSamples {
            Task { @MainActor in self.finalizeCapture() }
        }
    }

    // Nonisolated mirrors updated from main actor
    nonisolated(unsafe) var _isCapturing = false
    nonisolated(unsafe) var _captureData: [Float] = []
    nonisolated(unsafe) var _loopLengthSamples: Int = 0
    nonisolated(unsafe) var _capturedFrames: Int = 0

    func startRecording(loopLengthSamples: Int) {
        self.loopLengthSamples = loopLengthSamples
        _loopLengthSamples = loopLengthSamples
        _captureData = Array(repeating: 0.0, count: loopLengthSamples)
        _capturedFrames = 0
        _isCapturing = true
        state = .recording
    }

    func startOverdub() {
        guard state == .playing, loopBuffer != nil else { return }
        _loopLengthSamples = loopLengthSamples
        _captureData = Array(repeating: 0.0, count: loopLengthSamples)
        _capturedFrames = 0
        _isCapturing = true
        state = .overdubbing
    }

    func forceFinishRecording() {
        _isCapturing = false
        finalizeCapture()
    }

    private func finalizeCapture() {
        _isCapturing = false
        let count = _capturedFrames
        guard count > 0 else { state = .empty; return }

        let fmt = AVAudioFormat(standardFormatWithSampleRate: sampleRate, channels: 1)!
        let newBuf = AVAudioPCMBuffer(pcmFormat: fmt, frameCapacity: AVAudioFrameCount(count))!
        newBuf.frameLength = AVAudioFrameCount(count)
        let dst = newBuf.floatChannelData![0]

        if state == .overdubbing, let existing = loopBuffer {
            let src = existing.floatChannelData![0]
            let existingCount = Int(existing.frameLength)
            for i in 0..<count {
                dst[i] = _captureData[i] + src[i % existingCount]
            }
        } else {
            for i in 0..<count { dst[i] = _captureData[i] }
            loopLengthSamples = count
        }

        loopBuffer = newBuf
        scheduleLoop()
    }

    func startPlayback() {
        guard loopBuffer != nil else { return }
        scheduleLoop()
    }

    private func scheduleLoop() {
        guard let buf = loopBuffer else { return }
        playerNode.stop()
        playerNode.volume = isMuted ? 0 : volume
        playerNode.scheduleBuffer(buf, at: nil, options: .loops, completionHandler: nil)
        if !playerNode.isPlaying { playerNode.play() }
        state = .playing
    }

    func stop() {
        _isCapturing = false
        playerNode.stop()
        state = loopBuffer != nil ? .stopped : .empty
    }

    func clear() {
        _isCapturing = false
        playerNode.stop()
        loopBuffer = nil
        _captureData = []
        _capturedFrames = 0
        loopLengthSamples = 0
        state = .empty
    }

    func setVolume(_ v: Float) {
        volume = v
        playerNode.volume = isMuted ? 0 : v
    }

    func toggleMute() {
        isMuted.toggle()
        playerNode.volume = isMuted ? 0 : volume
    }
}
