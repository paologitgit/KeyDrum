// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "KeyLooper",
    platforms: [
        .macOS(.v14)
    ],
    targets: [
        .executableTarget(
            name: "KeyLooper",
            path: "Sources/KeyLooper",
            swiftSettings: [
                .unsafeFlags(["-parse-as-library"])
            ]
        )
    ]
)
