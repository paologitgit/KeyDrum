import SwiftUI

@MainActor
struct ContentView: View {
    @StateObject private var tempo = TempoManager()
    @StateObject private var midi = MIDIManager()
    @StateObject private var auManager = AUPluginManager()
    @State private var audio: AudioEngine?
    @State private var selectedTrack = 0
    @State private var bpmText = "120"
    @State private var devices: [String] = []
    @State private var selectedDevice = ""

    private let keyboard = KeyboardManager()

    var body: some View {
        VStack(spacing: 0) {
            headerBar
                .padding()
                .background(Color(nsColor: .windowBackgroundColor))

            Divider()

            if let audio {
                ScrollView {
                    VStack(spacing: 4) {
                        ForEach(0..<5, id: \.self) { i in
                            TrackRow(
                                track: audio.tracks[i],
                                index: i,
                                isSelected: selectedTrack == i,
                                midi: midi,
                                onRecord: { audio.recordOrOverdub(track: audio.tracks[i]) },
                                onStop:   { audio.tracks[i].stop() },
                                onClear:  { audio.tracks[i].clear() }
                            )
                            .contentShape(Rectangle())
                            .onTapGesture { selectedTrack = i }
                            .background(selectedTrack == i ? Color.accentColor.opacity(0.08) : Color.clear)
                            .cornerRadius(6)
                            .padding(.horizontal, 8)
                        }
                    }
                    .padding(.vertical, 8)
                }

                Divider()

                MixerView(audioEngine: audio, auManager: auManager)
            }

            Divider()
            statusBar
                .padding(.horizontal)
                .padding(.vertical, 6)
        }
        .onAppear { launch() }
        .onDisappear { keyboard.stop(); audio?.stop() }
    }

    // MARK: - Header

    private var headerBar: some View {
        HStack(spacing: 16) {
            Text("KeyLooper")
                .font(.headline)

            Divider().frame(height: 24)

            // BPM
            HStack(spacing: 6) {
                Text("BPM")
                    .foregroundStyle(.secondary)
                TextField("120", text: $bpmText)
                    .frame(width: 56)
                    .textFieldStyle(.roundedBorder)
                    .onSubmit {
                        if let v = Double(bpmText) { tempo.setBPM(v) }
                        bpmText = String(format: "%.1f", tempo.bpm)
                    }
                Text(String(format: "%.1f", tempo.bpm))
                    .foregroundStyle(.secondary)
                    .frame(width: 44, alignment: .leading)
                    .monospacedDigit()
            }

            Button("TAP") {
                tempo.tap()
                bpmText = String(format: "%.1f", tempo.bpm)
            }
            .buttonStyle(.borderedProminent)
            .keyboardShortcut("t", modifiers: [])

            Divider().frame(height: 24)

            HStack(spacing: 6) {
                Text("Beats").foregroundStyle(.secondary)
                Picker("", selection: $tempo.beatsPerLoop) {
                    ForEach([1, 2, 4, 8], id: \.self) { Text("\($0)").tag($0) }
                }
                .pickerStyle(.segmented)
                .frame(width: 140)
            }

            Spacer()

            if !devices.isEmpty {
                HStack(spacing: 6) {
                    Text("Gerät").foregroundStyle(.secondary)
                    Picker("", selection: $selectedDevice) {
                        ForEach(devices, id: \.self) { Text($0).tag($0) }
                    }
                    .frame(width: 220)
                    .onChange(of: selectedDevice) { _, name in
                        audio?.selectDevice(named: name)
                    }
                }
            }
        }
    }

    // MARK: - Status bar

    private var statusBar: some View {
        HStack(spacing: 14) {
            if midi.isLearning {
                Label("MIDI Learn: '\(midi.learnTarget)' — Taste drücken (ESC = Abbruch)", systemImage: "pianokeys.inverse")
                    .foregroundStyle(.orange)
                    .font(.caption)
            } else {
                shortcuts
            }
        }
    }

    private var shortcuts: some View {
        HStack(spacing: 12) {
            ForEach([
                ("1-5", "Spur"), ("R", "REC"), ("Spc", "Play/Stop"),
                ("S", "Alle Stop"), ("T", "Tap"), ("[/]", "Multiplikator"),
                ("M", "MIDI"), ("C", "Löschen")
            ], id: \.0) { key, label in
                HStack(spacing: 2) {
                    Text(key).bold()
                    Text(label).foregroundStyle(.secondary)
                }
                .font(.caption2)
            }
        }
    }

    // MARK: - Setup

    private func launch() {
        let eng = AudioEngine(tempoManager: tempo)
        audio = eng
        do {
            try eng.start()
        } catch {
            print("AudioEngine start error: \(error)")
        }
        devices = eng.availableDevices()
        selectedDevice = devices.first(where: {
            $0.localizedCaseInsensitiveContains("euphoria") ||
            $0.localizedCaseInsensitiveContains("behringer")
        }) ?? devices.first ?? ""

        setupKeyboard(audio: eng)
        setupMIDI(audio: eng)
    }

    private func setupKeyboard(audio: AudioEngine) {
        keyboard.onAction = { action in
            Task { @MainActor in handle(action: action, audio: audio) }
        }
        keyboard.start()
    }

    private func setupMIDI(audio: AudioEngine) {
        midi.onAction = { action in
            Task { @MainActor in handle(action: action, audio: audio) }
        }

        // ESC cancels MIDI learn
        NSEvent.addLocalMonitorForEvents(matching: .keyDown) { event in
            if event.keyCode == 53 && self.midi.isLearning {
                self.midi.cancelLearning()
                return nil
            }
            return event
        }
    }

    private func handle(action: String, audio: AudioEngine) {
        switch action {
        case "track0", "track1", "track2", "track3", "track4":
            selectedTrack = Int(String(action.last!))!
        case "record":
            audio.recordOrOverdub(track: audio.tracks[selectedTrack])
        case "play_stop":
            let t = audio.tracks[selectedTrack]
            if t.state == .playing || t.state == .overdubbing { t.stop() }
            else if t.state == .stopped { t.startPlayback() }
        case "stop_all":
            audio.tracks.forEach { $0.stop() }
        case "tap":
            tempo.tap()
            bpmText = String(format: "%.1f", tempo.bpm)
        case "mult_up":
            cycle(trackIndex: selectedTrack, up: true)
        case "mult_down":
            cycle(trackIndex: selectedTrack, up: false)
        case "midi_learn":
            if midi.isLearning { midi.cancelLearning() }
            else { midi.startLearning(target: "record_\(selectedTrack)") }
        case "clear":
            audio.tracks[selectedTrack].clear()
        default:
            // MIDI track-specific actions like record_0 ... record_4
            if action.hasPrefix("record_"), let i = Int(action.dropFirst(7)), i < 5 {
                audio.recordOrOverdub(track: audio.tracks[i])
            }
        }
    }

    private func cycle(trackIndex: Int, up: Bool) {
        guard let audio else { return }
        let t = audio.tracks[trackIndex]
        let all = LengthMultiplier.allCases
        guard let idx = all.firstIndex(of: t.multiplier) else { return }
        let newIdx = up ? min(idx + 1, all.count - 1) : max(idx - 1, 0)
        t.multiplier = all[newIdx]
    }
}

// MARK: - TrackRow

struct TrackRow: View {
    @ObservedObject var track: LooperTrack
    let index: Int
    let isSelected: Bool
    let midi: MIDIManager
    let onRecord: () -> Void
    let onStop: () -> Void
    let onClear: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            // Number + state dot
            ZStack {
                Circle()
                    .fill(stateColor.opacity(0.2))
                    .frame(width: 32, height: 32)
                Text("\(index + 1)")
                    .font(.headline)
                    .foregroundStyle(stateColor)
            }

            // Record button
            Button(recLabel) { onRecord() }
                .buttonStyle(.bordered)
                .tint(recTint)
                .frame(width: 88)

            // Stop / Clear
            Button("Stop", action: onStop)
                .disabled(track.state == .empty)
                .buttonStyle(.bordered)
            Button("Clear", action: onClear)
                .disabled(track.state == .empty)
                .buttonStyle(.bordered)

            Divider().frame(height: 26)

            // Multiplier
            HStack(spacing: 6) {
                Text("Länge").foregroundStyle(.secondary).font(.caption)
                Picker("", selection: $track.multiplier) {
                    ForEach(LengthMultiplier.allCases) { m in
                        Text(m.label).tag(m)
                    }
                }
                .pickerStyle(.segmented)
                .frame(width: 160)
            }

            Divider().frame(height: 26)

            // Volume + mute
            Button(action: { track.toggleMute() }) {
                Image(systemName: track.isMuted ? "speaker.slash.fill" : "speaker.wave.2.fill")
            }
            .buttonStyle(.borderless)
            Slider(value: Binding(
                get: { track.volume },
                set: { track.setVolume($0) }
            ), in: 0...1)
            .frame(width: 80)

            Spacer()

            // MIDI learn button
            let midiTarget = "record_\(index)"
            let isThisLearning = midi.isLearning && midi.learnTarget == midiTarget
            let hasBinding = midi.bindings[midiTarget] != nil

            Button(isThisLearning ? "Warte…" : (hasBinding ? "MIDI ✓" : "MIDI")) {
                if isThisLearning { midi.cancelLearning() }
                else { midi.startLearning(target: midiTarget) }
            }
            .buttonStyle(.bordered)
            .tint(isThisLearning ? .orange : (hasBinding ? .green : nil))
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
    }

    private var stateColor: Color {
        switch track.state {
        case .empty:      return .gray
        case .recording:  return .red
        case .playing:    return .green
        case .overdubbing: return .orange
        case .stopped:    return .blue
        }
    }

    private var recLabel: String {
        switch track.state {
        case .empty, .stopped: return "⏺ REC"
        case .recording:       return "■ Stop REC"
        case .playing:         return "⊕ OVERDUB"
        case .overdubbing:     return "■ Stop OD"
        }
    }

    private var recTint: Color? {
        switch track.state {
        case .recording:   return .red
        case .overdubbing: return .orange
        default:           return nil
        }
    }
}
