import AVFoundation

@MainActor
class AuxBus: ObservableObject, Identifiable {
    let id: Int
    let name: String

    let sendMixer = AVAudioMixerNode()
    var auPlugin: AVAudioUnit?
    let returnMixer = AVAudioMixerNode()

    @Published var returnLevel: Float = 0.8 {
        didSet { returnMixer.outputVolume = returnLevel }
    }
    @Published var isBypassed: Bool = false
    @Published var loadedPluginName: String = "– kein –"

    init(id: Int, name: String) {
        self.id = id
        self.name = name
    }
}
