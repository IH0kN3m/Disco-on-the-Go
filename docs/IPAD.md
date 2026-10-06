# iPad build

1. Open `apps/ipad/DiscoPort.xcodeproj` in Xcode.
2. Select the `DiscoPort` target. Under Signing and Capabilities, choose your development team and a unique bundle identifier.
3. Connect the iPad, enable Developer Mode, select it as the run destination, and run the `DiscoPort` scheme.

The app currently tests tap, hold, two-finger pan, pinch, reset, and interruption cancellation. The canvas is a diagnostic surface; it contains no game assets or gameplay.

```sh
make build-ipad        # Unsigned ARM64 device build; not installable as-is
make build-simulator   # Simulator build
make test-input        # Shared input tests on macOS
```

Device output: `artifacts/build/ipad/Build/Products/Debug-iphoneos/DiscoPort.app`.

Record real M4 device results separately from simulator results. Keep team IDs, device IDs, provisioning profiles, and signing certificates out of commits.
