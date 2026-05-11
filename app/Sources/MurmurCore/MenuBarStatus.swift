public enum MenuBarStatusState: Equatable, Sendable {
    case idle
    case listening
    case processing
    case error
}

public struct MenuBarStatusRendering: Equatable, Sendable {
    public let title: String
    public let systemSymbolName: String
    public let accessibilityDescription: String
    public let tooltipTitle: String
    public let statusMenuTitle: String
    public let toggleMenuTitle: String

    public init(
        title: String,
        systemSymbolName: String,
        accessibilityDescription: String,
        tooltipTitle: String,
        statusMenuTitle: String,
        toggleMenuTitle: String
    ) {
        self.title = title
        self.systemSymbolName = systemSymbolName
        self.accessibilityDescription = accessibilityDescription
        self.tooltipTitle = tooltipTitle
        self.statusMenuTitle = statusMenuTitle
        self.toggleMenuTitle = toggleMenuTitle
    }
}

public enum MenuBarStatusRenderer {
    public static func render(_ state: MenuBarStatusState) -> MenuBarStatusRendering {
        switch state {
        case .idle:
            return MenuBarStatusRendering(
                title: "Idle",
                systemSymbolName: "mic",
                accessibilityDescription: "Murmur idle",
                tooltipTitle: "Murmur — Idle",
                statusMenuTitle: "Status: Idle",
                toggleMenuTitle: "Start Listening"
            )
        case .listening:
            return MenuBarStatusRendering(
                title: "Listening",
                systemSymbolName: "record.circle.fill",
                accessibilityDescription: "Murmur listening",
                tooltipTitle: "Murmur — Listening",
                statusMenuTitle: "Status: Listening",
                toggleMenuTitle: "Stop Listening"
            )
        case .processing:
            return MenuBarStatusRendering(
                title: "Processing",
                systemSymbolName: "arrow.triangle.2.circlepath",
                accessibilityDescription: "Murmur processing",
                tooltipTitle: "Murmur — Processing",
                statusMenuTitle: "Status: Processing",
                toggleMenuTitle: "Start Listening"
            )
        case .error:
            return MenuBarStatusRendering(
                title: "Error",
                systemSymbolName: "exclamationmark.triangle.fill",
                accessibilityDescription: "Murmur error",
                tooltipTitle: "Murmur — Error",
                statusMenuTitle: "Status: Error",
                toggleMenuTitle: "Start Listening"
            )
        }
    }
}
