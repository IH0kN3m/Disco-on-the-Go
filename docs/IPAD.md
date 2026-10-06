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

For repeatable physical M4 deployment, put your authorized team and paired device identifier in `artifacts/local-ipad.json`:

```json
{"team_id": "YOURTEAMID", "device_identifier": "YOUR-PAIRED-DEVICE-ID"}
```

Run `make deploy-ipad`. It verifies the physical 13-inch M4 model, builds with automatic development signing, installs, and launches. The team needs Certificates, Identifiers, & Profiles access in Xcode. Xcode may create a development certificate/profile. The iPad must already be registered for that team; use Xcode's device destination if registration is needed. Keep the iPad unlocked for launch. Logs and device/signing configuration stay under `artifacts/`; signed products are under `artifacts/build/signed-ipad/`.

Verified on 6 October 2026: paid team signing, network installation and launch on a real 13-inch M4 with iPadOS 27.0. The user confirmed the requested harness gesture/layout checks work. Game execution and performance remain untested.

Record real M4 device results separately from simulator results. Keep team IDs, device IDs, provisioning profiles, and signing certificates out of commits.
