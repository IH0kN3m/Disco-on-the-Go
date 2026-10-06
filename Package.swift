// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "DiscoPortInput",
    platforms: [.macOS(.v13), .iOS(.v17)],
    products: [.library(name: "InputCore", targets: ["InputCore"])],
    targets: [
        .target(name: "InputCore", path: "runtime/InputCore"),
        .testTarget(name: "InputCoreTests", dependencies: ["InputCore"], path: "runtime/InputCoreTests")
    ]
)
