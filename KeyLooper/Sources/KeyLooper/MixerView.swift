import SwiftUI
import AVFoundation

struct MixerView: View {
    @ObservedObject var audioEngine: AudioEngine
    @ObservedObject var auManager: AUPluginManager

    var body: some View {
        ScrollView(.horizontal, showsIndicators: true) {
            HStack(alignment: .top, spacing: 2) {
                // Input channels
                ForEach(audioEngine.inputChannels) { ch in
                    InputChannelStrip(channel: ch)
                        .frame(width: 72)
                }

                Divider()

                // Looper channels
                ForEach(Array(audioEngine.looperChannels.enumerated()), id: \.offset) { idx, ch in
                    LooperChannelStrip(track: audioEngine.tracks[idx], channel: ch)
                        .frame(width: 72)
                }

                Divider()

                // AUX buses
                ForEach(audioEngine.auxBuses) { aux in
                    AuxBusStrip(aux: aux, auManager: auManager, audioEngine: audioEngine)
                        .frame(width: 100)
                }

                Divider()

                // Master
                MasterStrip(volume: Binding(
                    get: { audioEngine.masterVolume },
                    set: { audioEngine.setMasterVolume($0) }
                ))
                .frame(width: 72)
            }
            .padding(8)
        }
        .frame(height: 300)
        .background(Color(nsColor: .underPageBackgroundColor))
    }
}

// MARK: - Input Channel Strip

struct InputChannelStrip: View {
    @ObservedObject var channel: MixerChannel

    var body: some View {
        ChannelStripLayout(name: channel.name, isMuted: $channel.isMuted, isSoloed: $channel.isSoloed) {
            // Gain
            VStack(spacing: 2) {
                Text("GAIN").font(.system(size: 8)).foregroundStyle(.secondary)
                VerticalSlider(value: $channel.gain, range: 0...2, color: .yellow)
                    .frame(height: 50)
            }

            // AUX sends
            SendKnob(label: "A1", value: $channel.aux1Send)
            SendKnob(label: "A2", value: $channel.aux2Send)

            // Pan
            HStack(spacing: 2) {
                Text("PAN").font(.system(size: 8)).foregroundStyle(.secondary).frame(width: 24)
                Slider(value: $channel.pan, in: -1...1)
            }

            // Main fader
            FaderSection(volume: $channel.volume)
        }
    }
}

// MARK: - Looper Channel Strip

struct LooperChannelStrip: View {
    @ObservedObject var track: LooperTrack
    @ObservedObject var channel: MixerChannel

    var body: some View {
        ChannelStripLayout(name: channel.name, isMuted: $channel.isMuted, isSoloed: $channel.isSoloed) {
            // State indicator
            Circle()
                .fill(trackColor)
                .frame(width: 8, height: 8)

            // AUX sends
            SendKnob(label: "A1", value: $channel.aux1Send)
            SendKnob(label: "A2", value: $channel.aux2Send)

            // Pan
            HStack(spacing: 2) {
                Text("PAN").font(.system(size: 8)).foregroundStyle(.secondary).frame(width: 24)
                Slider(value: $channel.pan, in: -1...1)
            }

            // Main fader
            FaderSection(volume: $channel.volume)
        }
    }

    private var trackColor: Color {
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

struct AuxBusStrip: View {
    @ObservedObject var aux: AuxBus
    @ObservedObject var auManager: AUPluginManager
    let audioEngine: AudioEngine

    @State private var selectedPlugin: AUPluginInfo? = nil

    var body: some View {
        VStack(spacing: 6) {
            Text(aux.name)
                .font(.system(size: 10, weight: .bold))
                .foregroundStyle(.orange)

            // Plugin picker
            Picker("Plugin", selection: $selectedPlugin) {
                Text("– none –").tag(Optional<AUPluginInfo>.none)
                ForEach(auManager.effects) { plugin in
                    Text(plugin.name).tag(Optional(plugin))
                }
            }
            .labelsHidden()
            .font(.system(size: 9))
            .onChange(of: selectedPlugin) { _, plugin in
                loadPlugin(plugin)
            }

            // Bypass
            Toggle("Bypass", isOn: $aux.isBypassed)
                .toggleStyle(.button)
                .font(.system(size: 9))
                .controlSize(.mini)

            // Return fader
            VStack(spacing: 2) {
                Text("RTN").font(.system(size: 8)).foregroundStyle(.secondary)
                VerticalSlider(value: $aux.returnLevel, range: 0...1, color: .orange)
                    .frame(height: 100)
                Text(String(format: "%.0f%%", aux.returnLevel * 100))
                    .font(.system(size: 8)).foregroundStyle(.secondary)
            }

            Spacer()
        }
        .padding(6)
        .background(Color(nsColor: .controlBackgroundColor))
        .cornerRadius(6)
    }

    private func loadPlugin(_ plugin: AUPluginInfo?) {
        guard let plugin else {
            audioEngine.removeAUPlugin(from: aux)
            return
        }
        Task {
            if let unit = await auManager.instantiate(plugin) {
                audioEngine.insertAUPlugin(unit, into: aux)
                aux.loadedPluginName = plugin.name
            }
        }
    }
}

// MARK: - Master Strip

struct MasterStrip: View {
    @Binding var volume: Float

    var body: some View {
        VStack(spacing: 6) {
            Text("MASTER")
                .font(.system(size: 10, weight: .bold))
                .foregroundStyle(.white)

            Spacer()

            VerticalSlider(value: $volume, range: 0...1, color: .white)
                .frame(height: 120)

            Text(String(format: "%.0f%%", volume * 100))
                .font(.system(size: 8)).foregroundStyle(.secondary)
        }
        .padding(6)
        .background(Color(nsColor: .controlBackgroundColor))
        .cornerRadius(6)
    }
}

// MARK: - Reusable components

struct ChannelStripLayout<Content: View>: View {
    let name: String
    @Binding var isMuted: Bool
    @Binding var isSoloed: Bool
    @ViewBuilder let content: () -> Content

    var body: some View {
        VStack(spacing: 4) {
            Text(name)
                .font(.system(size: 9, weight: .bold))
                .lineLimit(1)
                .truncationMode(.middle)

            content()

            Spacer()

            HStack(spacing: 2) {
                Button("M") { isMuted.toggle() }
                    .buttonStyle(.bordered)
                    .controlSize(.mini)
                    .tint(isMuted ? .red : nil)
                Button("S") { isSoloed.toggle() }
                    .buttonStyle(.bordered)
                    .controlSize(.mini)
                    .tint(isSoloed ? .yellow : nil)
            }
        }
        .padding(4)
        .background(Color(nsColor: .controlBackgroundColor))
        .cornerRadius(6)
    }
}

struct FaderSection: View {
    @Binding var volume: Float

    var body: some View {
        VStack(spacing: 2) {
            VerticalSlider(value: $volume, range: 0...1, color: .green)
                .frame(height: 100)
            Text(String(format: "%.0f", volume * 100))
                .font(.system(size: 8)).foregroundStyle(.secondary)
        }
    }
}

struct SendKnob: View {
    let label: String
    @Binding var value: Float

    var body: some View {
        HStack(spacing: 4) {
            Text(label).font(.system(size: 8)).foregroundStyle(.secondary).frame(width: 14)
            Slider(value: $value, in: 0...1)
        }
    }
}

struct VerticalSlider: View {
    @Binding var value: Float
    let range: ClosedRange<Float>
    let color: Color

    var body: some View {
        GeometryReader { geo in
            ZStack(alignment: .bottom) {
                RoundedRectangle(cornerRadius: 3)
                    .fill(Color.gray.opacity(0.2))
                RoundedRectangle(cornerRadius: 3)
                    .fill(color.opacity(0.7))
                    .frame(height: geo.size.height * CGFloat((value - range.lowerBound) / (range.upperBound - range.lowerBound)))
            }
            .contentShape(Rectangle())
            .gesture(DragGesture(minimumDistance: 0)
                .onChanged { drag in
                    let pct = Float(1.0 - drag.location.y / geo.size.height)
                    value = range.lowerBound + max(0, min(1, pct)) * (range.upperBound - range.lowerBound)
                }
            )
        }
    }
}
