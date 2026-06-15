import CoreMIDI
import Foundation

struct MIDIBinding: Codable {
    let status: UInt8  // 0x90 = note, 0xB0 = CC
    let data1: UInt8
}

@MainActor
class MIDIManager: ObservableObject {
    @Published var isLearning = false
    @Published var learnTarget = ""
    @Published var bindings: [String: MIDIBinding] = [:]

    var onAction: ((String) -> Void)?

    private var client = MIDIClientRef()
    private var port = MIDIPortRef()

    init() {
        setupMIDI()
        loadBindings()
    }

    private func setupMIDI() {
        MIDIClientCreate("KeyLooper" as CFString, nil, nil, &client)

        let selfPtr = Unmanaged.passRetained(self)
        MIDIInputPortCreateWithProtocol(client, "KeyLooperIn" as CFString, .midi1_0, &port) { [selfPtr] evtList, _ in
            let manager = selfPtr.takeUnretainedValue()
            let list = evtList.pointee
            var pkt = list.packet
            for _ in 0..<list.numPackets {
                for word in pkt.words() {
                    let msgType = (word >> 28) & 0xF
                    guard msgType == 0x2 else { continue }
                    let status = UInt8((word >> 16) & 0xF0)
                    let data1  = UInt8((word >> 8) & 0xFF)
                    let data2  = UInt8(word & 0xFF)
                    guard status == 0x90 || status == 0xB0 else { continue }
                    guard data2 > 0 else { continue }  // ignore note-off / CC=0
                    let binding = MIDIBinding(status: status, data1: data1)
                    Task { @MainActor in manager.receive(binding: binding) }
                }
                pkt = MIDIEventList.next(packet: pkt)
            }
        }

        let srcCount = MIDIGetNumberOfSources()
        for i in 0..<srcCount {
            MIDIPortConnectSource(port, MIDIGetSource(i), nil)
        }
    }

    private func receive(binding: MIDIBinding) {
        if isLearning {
            bindings[learnTarget] = binding
            isLearning = false
            learnTarget = ""
            saveBindings()
            return
        }
        for (action, b) in bindings where b.status == binding.status && b.data1 == binding.data1 {
            onAction?(action)
        }
    }

    func startLearning(target: String) {
        learnTarget = target
        isLearning = true
    }

    func cancelLearning() {
        isLearning = false
        learnTarget = ""
    }

    private func saveBindings() {
        if let data = try? JSONEncoder().encode(bindings) {
            UserDefaults.standard.set(data, forKey: "midiBindings")
        }
    }

    private func loadBindings() {
        guard let data = UserDefaults.standard.data(forKey: "midiBindings"),
              let b = try? JSONDecoder().decode([String: MIDIBinding].self, from: data) else { return }
        bindings = b
    }
}
