# Device setup

Build the game first using [BUILD.md](BUILD.md). Device installation is separate and may require Apple network access for provisioning.

1. Pair the iPad with Xcode, enable Developer Mode, trust the Mac and leave the device unlocked for launch. USB or an already paired local-network connection can be used.
2. Sign in to your authorized Apple developer team in Xcode. The team needs Certificates, Identifiers & Profiles access, a registered device and the memory capabilities requested by this project. The verified setup uses a paid account.
3. Create the ignored `artifacts/local-ipad.json`:

```json
{"team_id": "YOURTEAMID", "device_identifier": "YOUR-PAIRED-DEVICE-ID", "bundle_id": "org.yourname.disco"}
```

Choose a unique `bundle_id` available to your team. Omitting it preserves the historical `org.discoport.engineprobe` identifier for existing installs; new builders should supply their own. The setting changes only the app target, and the built identifier is verified before selecting its asset container.

Use your own team ID and the paired identifier shown by `xcrun devicectl list devices`. Keep this configuration, command output, certificates, provisioning profiles and logs private.

```sh
python3 tools/deploy_ipad.py --engine --mip-limit 0 --lazy-scenes
```

The command validates a physical iPad on iPadOS 17+, signs with your team, installs, seeds the checked persistent asset directory and launches. It may create or update development provisioning. Native BC GPU support and actual memory headroom still determine whether the device can run the game; see [COMPATIBILITY.md](COMPATIBILITY.md).

The first asset transfer is about 9.6 GB. Later deployments skip it when the readiness manifest matches. Do not change your established bundle identifier or delete the app during a playthrough without backing up its Documents directory/saves. Development-signed apps are subject to profile expiry; plan renewal before travel. Increased-memory entitlements do not guarantee access to all installed RAM.

The working tree's unsigned output is not automatically installed. Device logs go to `Documents/native-engine.log`; retrieve only into ignored `artifacts/`. A returned process ID proves launch submission, not successful gameplay. Confirm loading a save, movement/input, UI alignment, a scene transition and save/reload on the actual device after runtime changes.

## Touch and dialogue

Tap the gamepad icon to show or hide the virtual controller. Drag the icon itself to move it; a drag does not toggle the controller. Its position is saved locally and kept inside the display's safe area after resizing or rotation. Empty space around the controls passes touches through to the game. Pinch zoom remains available on iPad.

The landscape layout uses the actual screen aspect. Newly created dialogue canvases and settings-driven layout resets receive the same fitting policy as the main UI. Dialogue font presets receive a 12.5% increase, rounded to whole font units, while retaining the selected dialogue-size setting. Other UI font settings are unchanged. The adapter adjusts runtime configuration before the first player frame; wrapping and scroll restoration use the game's existing code. This policy is specific to iPad; other models still need device testing.

## Separate diagnostics

These targets contain no complete game and are not part of `make port`:

| Command | Purpose |
| --- | --- |
| `make build-ipad` / `make deploy-ipad` | Original UIKit touch harness |
| `make build-simulator` | Simulator touch harness |
| `make deploy-unity-ipad` | Earlier recovered static-geometry diagnostic; see [UNITY.md](UNITY.md) |
| `make deploy-runtime-probe` | Original-runtime CPU experiment; see [NATIVE.md](NATIVE.md) |

The harness was verified on the physical M4 on 6 October 2026. Original gameplay was subsequently verified on 7 October; it is separate from the distorted early geometry diagnostic.
