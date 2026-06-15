import AVFoundation
import CoreAudio

@MainActor
class AudioEngine: ObservableObject {
    private let engine = AVAudioEngine()
    private let mainMixer = AVAudioMixerNode()
    private let masterMixer = AVAudioMixerNode()
    private let aux1BusMixer = AVAudioMixerNode()
    private let aux2BusMixer = AVAudioMixerNode()

    @Published var tracks: [LooperTrack] = []
    @Published var inputChannels: [MixerChannel] = []
    @Published var looperChannels: [MixerChannel] = []
    @Published var auxBuses: [AuxBus] = []
    var masterVolume: Float = 0.8

    private(set) var sampleRate: Double = 44100
    let tempoManager: TempoManager

    init(tempoManager: TempoManager) {
        self.tempoManager = tempoManager
        setup()
    }

    private func setup() {
        // Create input channels
        for i in 0..<2 {
            inputChannels.append(MixerChannel(id: i, name: "IN \(i + 1)"))
        }

        // Create looper channels
        for i in 0..<5 {
            looperChannels.append(MixerChannel(id: i, name: "LP \(i + 1)"))
        }

        // Create AUX buses
        for i in 0..<2 {
            auxBuses.append(AuxBus(id: i, name: "AUX \(i + 1)"))
        }

        // Attach all nodes
        engine.attach(mainMixer)
        engine.attach(masterMixer)
        engine.attach(aux1BusMixer)
        engine.attach(aux2BusMixer)

        for ch in inputChannels {
            engine.attach(ch.stripMixer)
            engine.attach(ch.aux1SendNode)
            engine.attach(ch.aux2SendNode)
        }

        for ch in looperChannels {
            engine.attach(ch.stripMixer)
            engine.attach(ch.aux1SendNode)
            engine.attach(ch.aux2SendNode)
        }

        for aux in auxBuses {
            engine.attach(aux.sendMixer)
            engine.attach(aux.returnMixer)
        }

        // Connect master chain: mainMixer → masterMixer → outputNode
        engine.connect(mainMixer, to: masterMixer, format: nil)
        engine.connect(masterMixer, to: engine.outputNode, format: nil)
        masterMixer.outputVolume = masterVolume

        // Connect AUX buses: collector → sendMixer → returnMixer → masterMixer
        engine.connect(aux1BusMixer, to: auxBuses[0].sendMixer, format: nil)
        engine.connect(auxBuses[0].sendMixer, to: auxBuses[0].returnMixer, format: nil)
        engine.connect(auxBuses[0].returnMixer, to: masterMixer, format: nil)

        engine.connect(aux2BusMixer, to: auxBuses[1].sendMixer, format: nil)
        engine.connect(auxBuses[1].sendMixer, to: auxBuses[1].returnMixer, format: nil)
        engine.connect(auxBuses[1].returnMixer, to: masterMixer, format: nil)

        // Connect input channel strips
        let inputNode = engine.inputNode
        let fmt = inputNode.outputFormat(forBus: 0)
        sampleRate = fmt.sampleRate > 0 ? fmt.sampleRate : 44100

        for (i, ch) in inputChannels.enumerated() {
            // stripMixer → mainMixer
            engine.connect(ch.stripMixer, to: mainMixer, format: nil)
            // aux sends → aux bus collectors
            engine.connect(ch.aux1SendNode, to: aux1BusMixer, format: nil)
            engine.connect(ch.aux2SendNode, to: aux2BusMixer, format: nil)
            // Input is fed via the tap below; no direct node connection for mic input
            _ = i
        }

        // Connect looper channel strips
        for ch in looperChannels {
            engine.connect(ch.stripMixer, to: mainMixer, format: nil)
            engine.connect(ch.aux1SendNode, to: aux1BusMixer, format: nil)
            engine.connect(ch.aux2SendNode, to: aux2BusMixer, format: nil)
        }

        // Create looper tracks connected to their channel strips
        for i in 0..<5 {
            let t = LooperTrack(id: i, engine: engine, mixer: looperChannels[i].stripMixer)
            t.configure(sampleRate: sampleRate)
            tracks.append(t)
        }

        // Input tap for recording
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

    func setMasterVolume(_ v: Float) {
        masterVolume = v
        masterMixer.outputVolume = v
    }

    func insertAUPlugin(_ unit: AVAudioUnit, into aux: AuxBus) {
        let fmt = aux.sendMixer.outputFormat(forBus: 0)
        engine.disconnectNodeOutput(aux.sendMixer)
        engine.attach(unit)
        engine.connect(aux.sendMixer, to: unit, format: fmt)
        engine.connect(unit, to: aux.returnMixer, format: fmt)
        aux.auPlugin = unit
    }

    func removeAUPlugin(from aux: AuxBus) {
        let fmt = aux.sendMixer.outputFormat(forBus: 0)
        if let au = aux.auPlugin {
            engine.disconnectNodeOutput(aux.sendMixer)
            engine.disconnectNodeOutput(au)
            engine.detach(au)
            aux.auPlugin = nil
        }
        engine.connect(aux.sendMixer, to: aux.returnMixer, format: fmt)
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
