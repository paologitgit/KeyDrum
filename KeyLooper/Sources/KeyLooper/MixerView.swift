import SwiftUI
import AVFoundation

struct MixerView: View {
    @ObservedObject var audioEngine: AudioEngine
    @ObservedObject var auManager: AUPluginManager

    var body: some View {
        ScrollView(.horizontal, showsIndicators: true) {
            HStack(alignment: .top, spacing: 2) {
                ForEach(Array(audioEngine.inputChannels.enumerated()), id: \.offset) { i, ch in
                    InputStrip(channel: ch, onGainChange: { g in
                        audioEngine.setInputGain(g, channel: i)
                    })
                    .frame(width: 76)
                }

                stripDivider

                ForEach(Array(zip(audioEngine.tracks, audioEngine.looperChannels)), id: \.0.id) { track, ch in
                    LooperStrip(track: track, channel: ch)
                        .frame(width: 76)
                }

                stripDivider

                ForEach(audioEngine.auxBuses) { aux in
                    AuxStrip(aux: aux, auManager: auManager, audioEngine: audioEngine)
                        .frame(width: 110)
                }

                stripDivider

                MasterStrip(volume: Binding(
                    get: { audioEngine.masterVolume },
                    set: { audioEngine.masterVolume = $0; audioEngine.setMasterVolume($0) }
                ))
                .frame(width: 76)
            }
            .padding(8)
        }
        .frame(height: 290)
        .background(Color(nsColor: .underPageBackgroundColor))
    }

    private var stripDivider: some View {
        Divider().padding(.vertical, 4)
    }
}

// MARK: - Input Channel Strip

struct InputStrip: View {
    @ObservedObject var channel: MixerChannel
    let onGainChange: (Float) -> Void

    var body: some View {
        StripShell(name: channel.name, isMuted: $channel.isMuted, isSoloed: $channel.isSoloed) {
            VStack(spacing: 3) {
                Label("GAIN", systemImage: "dial.low")
                    .font(.system(size: 7)).foregroundStyle(.secondary).labelStyle(.titleOnly)
                VerticalSlider(value: $channel.gain, range: 0...2, color: .yellow)
                    .frame(height: 44)
                    .onChange(of: channel.gain) { _, g in onGainChange(g) }
            }

            SendRow(label: "A1", value: $channel.aux1Send)
            SendRow(label: "A2", value: $channel.aux2Send)
            FaderRow(volume: $channel.volume)
        }
    }
}

// MARK: - Looper Channel Strip

struct LooperStrip: View {
    @ObservedObject var track: LooperTrack
    @ObservedObject var channel: MixerChannel

    var body: some View {
        StripShell(name: channel.name, isMuted: $channel.isMuted, isSoloed: $channel.isSoloed) {
            Circle()
                .fill(stateColor)
                .frame(width: 8, height: 8)
                .padding(.top, 4)

            SendRow(label: "A1", value: $channel.aux1Send)
            SendRow(label: "A2", value: $channel.aux2Send)
            FaderRow(volume: $channel.volume)
        }
    }

    private var stateColor: Color {
        switch track.state {
        case .empty: return .gray
        case .recording: return .red
        case .playing: return .green
        case .overdubbing: return .orange
        case .stopped: return .blue
        }
    }
}

// MARK: - AUX Bus Strip

struct AuxStrip: View {
    @ObservedObject var aux: AuxBus
    @ObservedObject var auManager: AUPluginManager
    let audioEngine: AudioEngine

    @State private var selectedPlugin: AUPluginInfo? = nil

    var body: some View {
        VStack(spacing: 5) {
            Text(aux.name)
                .font(.system(size: 10, weight: .bold))
                .foregroundStyle(.orange)

            Picker("", selection: $selectedPlugin) {
                Text("– kein –").tag(Optional<AUPluginInfo>.none)
                ForEach(auManager.effects) { p in
                    Text(p.name).tag(Optional(p))
                }
            }
            .labelsHidden()
            .font(.system(size: 9))
            .frame(maxWidth: .infinity)
            .onChange(of: selectedPlugin) { _, plugin in
                Task { await loadPlugin(plugin) }
            }

            Toggle("Bypass", isOn: $aux.isBypassed)
                .toggleStyle(.button)
                .font(.system(size: 9))
                .controlSize(.mini)

            Spacer()

            VStack(spacing: 2) {
                Text("RTN").font(.system(size: 8)).foregroundStyle(.secondary)
                VerticalSlider(value: $aux.returnLevel, range: 0...1, color: .orange)
                    .frame(height: 90)
                Text(String(format: "%.0f%%", aux.returnLevel * 100))
                    .font(.system(size: 8)).foregroundStyle(.secondary).monospacedDigit()
            }
        }
        .padding(5)
        .background(Color(nsColor: .controlBackgroundColor))
        .cornerRadius(6)
    }

    private func loadPlugin(_ plugin: AUPluginInfo?) async {
        guard let plugin else {
            audioEngine.removeAUPlugin(from: aux)
            return
        }
        if let unit = await auManager.instantiate(plugin) {
            audioEngine.insertAUPlugin(unit, into: aux)
            aux.loadedPluginName = plugin.name
        }
    }
}

// MARK: - Master Strip

struct MasterStrip: View {
    @Binding var volume: Float

    var body: some View {
        VStack(spacing: 5) {
            Text("MASTER")
                .font(.system(size: 10, weight: .bold))

            Spacer()

            VStack(spacing: 2) {
                VerticalSlider(value: $volume, range: 0...1, color: .white)
                    .frame(height: 110)
                Text(String(format: "%.0f%%", volume * 100))
                    .font(.system(size: 8)).foregroundStyle(.secondary).monospacedDigit()
            }
        }
        .padding(5)
        .background(Color(nsColor: .controlBackgroundColor))
        .cornerRadius(6)
    }
}

// MARK: - Reusable components

struct StripShell<Content: View>: View {
    let name: String
    @Binding var isMuted: Bool
    @Binding var isSoloed: Bool
    @ViewBuilder let content: () -> Content

    var body: some View {
        VStack(spacing: 4) {
            Text(name)
                .font(.system(size: 9, weight: .bold))
                .lineLimit(1)

            content()

            Spacer(minLength: 0)

            HStack(spacing: 2) {
                Button("M") { isMuted.toggle() }
                    .buttonStyle(.bordered).controlSize(.mini)
                    .tint(isMuted ? .red : nil)
                Button("S") { isSoloed.toggle() }
                    .buttonStyle(.bordered).controlSize(.mini)
                    .tint(isSoloed ? .yellow : nil)
            }
        }
        .padding(5)
        .background(Color(nsColor: .controlBackgroundColor))
        .cornerRadius(6)
    }
}

struct FaderRow: View {
    @Binding var volume: Float
    var body: some View {
        VStack(spacing: 2) {
            VerticalSlider(value: $volume, range: 0...1, color: .green)
                .frame(height: 90)
            Text(String(format: "%.0f", volume * 100))
                .font(.system(size: 8)).foregroundStyle(.secondary).monospacedDigit()
        }
    }
}

struct SendRow: View {
    let label: String
    @Binding var value: Float
    var body: some View {
        HStack(spacing: 3) {
            Text(label).font(.system(size: 8)).foregroundStyle(.secondary).frame(width: 14)
            Slider(value: $value, in: 0...1)
        }
    }
}

struct VerticalSlider: View {
    @Binding var value: Float
    var range: ClosedRange<Float> = 0...1
    var color: Color = .green

    var body: some View {
        GeometryReader { geo in
            ZStack(alignment: .bottom) {
                RoundedRectangle(cornerRadius: 3).fill(Color.gray.opacity(0.15))
                RoundedRectangle(cornerRadius: 3)
                    .fill(color.opacity(0.75))
                    .frame(height: geo.size.height * CGFloat(
                        (value - range.lowerBound) / (range.upperBound - range.lowerBound)
                    ))
            }
            .contentShape(Rectangle())
            .gesture(DragGesture(minimumDistance: 0).onChanged { drag in
                let pct = Float(1.0 - drag.location.y / geo.size.height)
                value = range.lowerBound + max(0, min(1, pct)) * (range.upperBound - range.lowerBound)
            })
        }
    }
}
