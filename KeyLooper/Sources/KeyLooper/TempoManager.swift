import Foundation

class TempoManager: ObservableObject {
    @Published var bpm: Double = 120.0
    @Published var beatsPerLoop: Int = 4

    private var tapTimes: [Date] = []
    private let maxTapHistory = 8

    var masterLoopDuration: TimeInterval {
        (60.0 / bpm) * Double(beatsPerLoop)
    }

    func masterLoopSamples(sampleRate: Double) -> Int {
        Int(masterLoopDuration * sampleRate)
    }

    func tap() {
        let now = Date()

        if let last = tapTimes.last, now.timeIntervalSince(last) > 3.0 {
            tapTimes = []
        }

        tapTimes.append(now)
        if tapTimes.count > maxTapHistory { tapTimes.removeFirst() }
        guard tapTimes.count >= 2 else { return }

        let intervals = zip(tapTimes, tapTimes.dropFirst()).map { $1.timeIntervalSince($0) }
        let avg = intervals.reduce(0, +) / Double(intervals.count)
        bpm = max(40, min(240, 60.0 / avg))
    }

    func setBPM(_ newBPM: Double) {
        bpm = max(40, min(240, newBPM))
        tapTimes = []
    }
}
