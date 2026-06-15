import AVFoundation

struct AUPluginInfo: Identifiable, Hashable {
    var id: String { name }
    let name: String
    let component: AVAudioUnitComponent

    static func == (lhs: AUPluginInfo, rhs: AUPluginInfo) -> Bool { lhs.name == rhs.name }
    func hash(into hasher: inout Hasher) { hasher.combine(name) }
}

@MainActor
class AUPluginManager: ObservableObject {
    @Published var effects: [AUPluginInfo] = []

    init() {
        let desc = AudioComponentDescription(
            componentType: kAudioUnitType_Effect,
            componentSubType: 0,
            componentManufacturer: 0,
            componentFlags: 0,
            componentFlagsMask: 0
        )
        effects = AVAudioUnitComponentManager.shared()
            .components(matching: desc)
            .map { AUPluginInfo(name: $0.name, component: $0) }
            .sorted { $0.name < $1.name }
    }

    func instantiate(_ info: AUPluginInfo) async -> AVAudioUnit? {
        await withCheckedContinuation { cont in
            AVAudioUnit.instantiate(with: info.component.audioComponentDescription, options: []) { unit, _ in
                cont.resume(returning: unit)
            }
        }
    }
}
