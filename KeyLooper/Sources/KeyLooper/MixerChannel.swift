import AVFoundation

@MainActor
class MixerChannel: ObservableObject, Identifiable {
    let id: Int
    let name: String

    let stripMixer = AVAudioMixerNode()
    let aux1SendNode = AVAudioMixerNode()
    let aux2SendNode = AVAudioMixerNode()

    @Published var volume: Float = 0.8 {
        didSet { if !isMuted { stripMixer.outputVolume = volume } }
    }
    @Published var isMuted: Bool = false {
        didSet { stripMixer.outputVolume = isMuted ? 0 : volume }
    }
    @Published var isSoloed: Bool = false
    @Published var aux1Send: Float = 0.0 {
        didSet { aux1SendNode.outputVolume = aux1Send }
    }
    @Published var aux2Send: Float = 0.0 {
        didSet { aux2SendNode.outputVolume = aux2Send }
    }
    // Input channels only
    @Published var gain: Float = 1.0

    init(id: Int, name: String) {
        self.id = id
        self.name = name
    }
}
