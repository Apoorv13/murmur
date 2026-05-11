// swift-tools-version: 5.9

import PackageDescription

let package = Package(
    name: "MurmurApp",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .executable(
            name: "Murmur",
            targets: ["Murmur"]
        )
    ],
    targets: [
        .target(
            name: "MurmurCore",
            path: "Sources/MurmurCore"
        ),
        .executableTarget(
            name: "Murmur",
            dependencies: ["MurmurCore"],
            path: "Sources/Murmur"
        )
    ]
)
