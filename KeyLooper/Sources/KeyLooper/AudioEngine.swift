import AVFoundation
import CoreAudio

@MainActor
class AudioEngine: ObservableObject {
    private let engine = AVAudioEngine()
    private let mainMixer = AVAudioMixerNode()
    private let masterMixer = AVAudioMixerNode()

    @Published var tracks: [LooperTrack] = []
    @Published var inputChannels: [MixerChannel] = []
    @Published var looperChannels: [MixerChannel] = []
    @Published var auxBuses: [AuxBus] = []
    @Published var masterVolume: Float = 0.8

    private var inputGainNodes: [AVAudioMixerNode] = []
    private(set) var sampleRate: Double = 44100
    let tempoManager: TempoManager

    init(tempoManager: TempoManager) {
        self.tempoManager = tempoManager
        setup()
    }

    private func setup() {
        // Attach top-level mixers
        engine.attach(mainMixer)
        engine.attach(masterMixer)
        masterMixer.outputVolume = masterVolume
        engine.connect(mainMixer, to: masterMixer, format: nil)
        engine.connect(masterMixer, to: engine.outputNode, format: nil)

        // AUX buses
        for i in 0..<2 {
            let aux = AuxBus(id: i, name: "AUX \(i + 1)")
            engine.attach(aux.sendMixer)
            engine.attach(aux.returnMixer)
            aux.sendMixer.outputVolume = 1.0
            aux.returnMixer.outputVolume = aux.returnLevel
            // sendMixer → returnMixer (no plugin yet)
            engine.connect(aux.sendMixer, to: aux.returnMixer, format: nil)
            engine.connect(aux.returnMixer, to: mainMixer, format: nil)
            auxBuses.append(aux)
        }

        let inputNode = engine.inputNode
        let fmt = inputNode.outputFormat(forBus: 0)
        sampleRate = fmt.sampleRate > 0 ? fmt.sampleRate : 44100

        // Input channels (2)
        for i in 0..<2 {
            let ch = MixerChannel(id: i, name: "IN \(i + 1)")
            let gainNode = AVAudioMixerNode()
            engine.attach(gainNode)
            engine.attach(ch.stripMixer)
            engine.attach(ch.aux1SendNode)
            engine.attach(ch.aux2SendNode)

            // inputNode(bus i) → gainNode → stripMixer → mainMixer
            engine.connect(inputNode, to: gainNode, fromBus: i < inputNode.numberOfInputs ? i : 0, toBus: 0, format: fmt)
            engine.connect(gainNode, to: ch.stripMixer, format: nil)
            engine.connect(ch.stripMixer, to: mainMixer, format: nil)

            // sends
            engine.connect(ch.stripMixer, to: ch.aux1SendNode, format: nil)
            engine.connect(ch.stripMixer, to: ch.aux2SendNode, format: nil)
            engine.connect(ch.aux1SendNode, to: auxBuses[0].sendMixer, format: nil)
            engine.connect(ch.aux2SendNode, to: auxBuses[1].sendMixer, format: nil)

            ch.aux1SendNode.outputVolume = 0
            ch.aux2SendNode.outputVolume = 0
            gainNode.outputVolume = 1.0

            inputGainNodes.append(gainNode)
            inputChannels.append(ch)
        }

        // Record tap only on bus 0 (mono input)
        inputNode.installTap(onBus: 0, bufferSize: 512, format: fmt) { [weak self] buffer, _ in
            guard let self, let ch = buffer.floatChannelData?[0] else { return }
            let n = Int(buffer.frameLength)
            for track in self.tracks { track.feedInput(ch, count: n) }
        }

        // Looper tracks (5)
        for i in 0..<5 {
            let ch = MixerChannel(id: i, name: "LP \(i + 1)")
            engine.attach(ch.stripMixer)
            engine.attach(ch.aux1SendNode)
            engine.attach(ch.aux2SendNode)

            let track = LooperTrack(id: i, engine: engine, channelStrip: ch.stripMixer, mainMixer: mainMixer)
            track.configure(sampleRate: sampleRate)

            // strip → mainMixer and sends
            engine.connect(ch.stripMixer, to: mainMixer, format: nil)
            engine.connect(ch.stripMixer, to: ch.aux1SendNode, format: nil)
            engine.connect(ch.stripMixer, to: ch.aux2SendNode, format: nil)
            engine.connect(ch.aux1SendNode, to: auxBuses[0].sendMixer, format: nil)
            engine.connect(ch.aux2SendNode, to: auxBuses[1].sendMixer, format: nil)

            ch.aux1SendNode.outputVolume = 0
            ch.aux2SendNode.outputVolume = 0

            looperChannels.append(ch)
            tracks.append(track)
        }
    }

    func start() throws {
        try engine.start()
    }

    func stop() {
        engine.stop()
    }

    func setMasterVolume(_ v: Float) {
        masterMixer.outputVolume = v
    }

    func setInputGain(_ gain: Float, channel: Int) {
        guard channel < inputGainNodes.count else { return }
        inputGainNodes[channel].outputVolume = gain
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

    // MARK: - AU Plugin management

    func insertAUPlugin(_ unit: AVAudioUnit, into aux: AuxBus) {
        // Disconnect existing chain
        engine.disconnectNodeOutput(aux.sendMixer)
        if let existing = aux.auPlugin {
            engine.disconnectNodeOutput(existing)
            engine.detach(existing)
        }
        // Insert: sendMixer → AU → returnMixer
        engine.attach(unit)
        engine.connect(aux.sendMixer, to: unit, format: nil)
        engine.connect(unit, to: aux.returnMixer, format: nil)
        aux.auPlugin = unit
    }

    func removeAUPlugin(from aux: AuxBus) {
        engine.disconnectNodeOutput(aux.sendMixer)
        if let au = aux.auPlugin {
            engine.disconnectNodeOutput(au)
            engine.detach(au)
            aux.auPlugin = nil
        }
        engine.connect(aux.sendMixer, to: aux.returnMixer, format: nil)
        aux.loadedPluginName = "– kein –"
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
            guard ok == noErr, let devName = cfName as String?,
                  devName.localizedCaseInsensitiveContains(name) else { continue }

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
