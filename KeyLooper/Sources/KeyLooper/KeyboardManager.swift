import AppKit

class KeyboardManager {
    private var localMonitor: Any?
    var onAction: ((String) -> Void)?

    func start() {
        localMonitor = NSEvent.addLocalMonitorForEvents(matching: .keyDown) { [weak self] event in
            if let action = self?.action(for: event) {
                self?.onAction?(action)
                return nil  // consume event
            }
            return event
        }
    }

    func stop() {
        if let m = localMonitor { NSEvent.removeMonitor(m) }
    }

    private func action(for event: NSEvent) -> String? {
        guard !event.isARepeat else { return nil }
        // Ignore if editing a text field
        if let first = NSApp.keyWindow?.firstResponder, first is NSTextView { return nil }

        switch event.keyCode {
        case 18: return "track0"      // 1
        case 19: return "track1"      // 2
        case 20: return "track2"      // 3
        case 21: return "track3"      // 4
        case 23: return "track4"      // 5
        case 15: return "record"      // R
        case 49: return "play_stop"   // Space
        case 1:  return "stop_all"    // S
        case 17: return "tap"         // T
        case 33: return "mult_down"   // [
        case 30: return "mult_up"     // ]
        case 46: return "midi_learn"  // M
        case 8:  return "clear"       // C
        default: return nil
        }
    }
}
