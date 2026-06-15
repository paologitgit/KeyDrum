import AVFoundation
import CoreAudio

@MainActor
class AudioEngine: ObservableObject {
    private let engine = AVAudioEngine()
    private let mainMixer = AVAudioMixerNode()
    @Published var tracks: [LooperTrack] = []

    private(set) var sampleRate: Double = 44100
    let tempoManager: TempoManager

    init(tempoManager: TempoManager) {
        self.tempoManager = tempoManager
        setup()
    }

    private func setup() {
        engine.attach(mainMixer)
        engine.connect(mainMixer, to: engine.outputNode, format: nil)

        let inputNode = engine.inputNode
        let fmt = inputNode.outputFormat(forBus: 0)
        sampleRate = fmt.sampleRate > 0 ? fmt.sampleRate : 44100

        for i in 0..<5 {
            let t = LooperTrack(id: i, engine: engine, mixer: mainMixer)
            t.configure(sampleRate: sampleRate)
            tracks.append(t)
        }

        inputNode.installTap(onBus: 0, bufferSize: 512, format: fmt) { [weak self] buffer, _ in
            guard let self, let ch = buffer.floatChannelData?[0] else { return }
            let n = Int(buffer.frameLength)
            for track in self.tracks {
                track.feedInput(ch, count: n)
            }
        }
    }

    func start() throws {
        try engine.start()
    }

    func stop() {
        engine.stop()
    }

    func recordOrOverdub(track: LooperTrack) {
        let loopSamples = tempoManager.masterLoopSamples(sampleRate: sampleRate) * track.multiplier.rawValue
        switch track.state {
        case .empty, .stopped:
            track.startRecording(loopLengthSamples: loopSamples)
        case .recording, .overdubbing:
            track.forceFinishRecording()
        case .playing:
            track.startOverdub()
        }
    }

    // MARK: - CoreAudio device enumeration

    func availableDevices() -> [String] {
        var addr = AudioObjectPropertyAddress(
            mSelector: kAudioHardwarePropertyDevices,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain)
        var size: UInt32 = 0
        AudioObjectGetPropertyDataSize(AudioObjectID(kAudioObjectSystemObject), &addr, 0, nil, &size)
        let count = Int(size) / MemoryLayout<AudioDeviceID>.size
        var ids = [AudioDeviceID](repeating: 0, count: count)
        AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject), &addr, 0, nil, &size, &ids)

        return ids.compactMap { deviceID -> String? in
            var nameAddr = AudioObjectPropertyAddress(
                mSelector: kAudioDevicePropertyDeviceNameCFString,
                mScope: kAudioObjectPropertyScopeGlobal,
                mElement: kAudioObjectPropertyElementMain)
            var nameSize = UInt32(MemoryLayout<CFString?>.size)
            var name: CFString? = nil
            let status = withUnsafeMutablePointer(to: &name) { ptr -> OSStatus in
                ptr.withMemoryRebound(to: UInt8.self, capacity: MemoryLayout<CFString?>.size) { raw in
                    AudioObjectGetPropertyData(deviceID, &nameAddr, 0, nil, &nameSize, raw)
                }
            }
            return status == noErr ? (name as String?) : nil
        }
    }

    func selectDevice(named name: String) {
        var addr = AudioObjectPropertyAddress(
            mSelector: kAudioHardwarePropertyDevices,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain)
        var size: UInt32 = 0
        AudioObjectGetPropertyDataSize(AudioObjectID(kAudioObjectSystemObject), &addr, 0, nil, &size)
        let count = Int(size) / MemoryLayout<AudioDeviceID>.size
        var ids = [AudioDeviceID](repeating: 0, count: count)
        AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject), &addr, 0, nil, &size, &ids)

        for deviceID in ids {
            var nameAddr = AudioObjectPropertyAddress(
                mSelector: kAudioDevicePropertyDeviceNameCFString,
                mScope: kAudioObjectPropertyScopeGlobal,
                mElement: kAudioObjectPropertyElementMain)
            var nameSize = UInt32(MemoryLayout<CFString?>.size)
            var cfName: CFString? = nil
            let ok = withUnsafeMutablePointer(to: &cfName) { ptr -> OSStatus in
                ptr.withMemoryRebound(to: UInt8.self, capacity: MemoryLayout<CFString?>.size) { raw in
                    AudioObjectGetPropertyData(deviceID, &nameAddr, 0, nil, &nameSize, raw)
                }
            }
            guard ok == noErr, let devName = cfName as String?, devName.localizedCaseInsensitiveContains(name) else { continue }

            var id = deviceID
            var inAddr = AudioObjectPropertyAddress(
                mSelector: kAudioHardwarePropertyDefaultInputDevice,
                mScope: kAudioObjectPropertyScopeGlobal,
                mElement: kAudioObjectPropertyElementMain)
            AudioObjectSetPropertyData(AudioObjectID(kAudioObjectSystemObject), &inAddr, 0, nil,
                                       UInt32(MemoryLayout<AudioDeviceID>.size), &id)
            var outAddr = AudioObjectPropertyAddress(
                mSelector: kAudioHardwarePropertyDefaultOutputDevice,
                mScope: kAudioObjectPropertyScopeGlobal,
                mElement: kAudioObjectPropertyElementMain)
            AudioObjectSetPropertyData(AudioObjectID(kAudioObjectSystemObject), &outAddr, 0, nil,
                                       UInt32(MemoryLayout<AudioDeviceID>.size), &id)
            break
        }
    }
}
