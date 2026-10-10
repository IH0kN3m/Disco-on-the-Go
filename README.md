# Disco mobile port

Build native iPad and Android versions locally from your own macOS `Disco.app`. This unofficial project distributes original build tools and compatibility adapters, **not the game, Unity, extracted code, assets, IPA, APK or OBB**.

The previous build runs on a stock **13-inch iPad Pro M4, 16 GB, iPadOS 27**. Opening dialogue, textured gameplay, tap movement, pinch zoom, the virtual controller, saving, scene transitions and full-screen 4:3 landscape have been verified. A complete playthrough and long-session stability have not. See [compatibility](docs/COMPATIBILITY.md) for other iPads and current limits.

## Android

The Android port runs original gameplay on the Galaxy Tab S10 Ultra and Retroid Pocket 5. Menus, dialogue and rooms are tested; Samsung outdoor rendering and two-finger object highlighting, and Retroid quick-save, are verified. Full playthrough, later scenes and sustained performance remain untested. Samsung decompresses unsupported BC textures; the Retroid GPU supports them directly. See [Android status and local build steps](docs/ANDROID.md). Generated APKs and game assets remain private. Build with `make doctor PLATFORM=android` and `make port PLATFORM=android` after the [Android tool setup](docs/ANDROID.md#build-requirements). Windows game files are not required.

## Requirements

- Mac with **Xcode 27.x**, selected with `xcode-select`, and Python **3.11+**. Tested: Xcode 27.0, Python 3.14.7 on Apple silicon.
- **Unity 2020.3.12f1** with iOS Build Support, a valid applicable Unity license, and Rosetta for this Intel editor. The setup command downloads approximately 4.2 GB from Unity; it does not activate a license.
- Your own compatible macOS game at **`reference/Disco.app`**. The build checks exact native-module and metadata fingerprints before proceeding; a different revision is rejected. See [input requirements](docs/BUILD.md#game-input).
- At least **60 GiB free** on the Mac after installing tools. Device deployment also needs approximately 10 GB of asset storage plus saves and installation headroom.
- For installation: an Apple development signing team with the required memory capabilities, a paired physical iPad, Developer Mode, and an unlocked device. The tested setup uses a paid account.

## Build

Run from the repository root. First place your game at `reference/Disco.app`, then:

```sh
make setup-scenes     # Install pinned local Python dependencies
make setup-unity      # Download and verify the pinned Unity editor + iOS module
make doctor           # Validate input revision and installed build tools
make port             # Complete unsigned build; no device access or downloads
```

The build exports an empty original Unity host, derives the runtime/plugins from your copy, preserves game object/resource bodies while retagging platform headers, enables native BC textures, and builds the iOS app. Scene recovery, Ghidra and decompilation are **not** prerequisites. The original app is read only; a before/after fingerprint checks that it was not changed.

Outputs and per-step logs stay under ignored `artifacts/`. An unsigned build is not installable. [Build and troubleshooting](docs/BUILD.md) covers licensing, paths, rebuilding and the distinction between reproducible steps and byte-identical output.

## Install and play

Create `artifacts/local-ipad.json` with your own values:

```json
{"team_id": "YOURTEAMID", "device_identifier": "YOUR-PAIRED-DEVICE-ID", "bundle_id": "org.yourname.disco"}
```

Choose a unique `bundle_id` available to your team. Existing installations should retain their current identifier to keep their saves. Then, with the iPad paired and unlocked:

```sh
python3 tools/deploy_ipad.py --engine --mip-limit 0 --lazy-scenes
```

This signs, installs, uploads the local assets, and launches the app. Initial transfer is large; later deployments skip it when the manifest matches. Keep the bundle identifier consistent to preserve the app's saves, and back up saves before replacing or deleting the app. [Device setup](docs/IPAD.md) has details.

Tap to move/interact; pinch to zoom. Tap the small gamepad icon to show or hide dual sticks, a D-pad, ABXY, shoulders, triggers and Menu; drag the icon itself to reposition it. Hiding the pad restores direct touch. Dialogue font presets receive a modest readability increase; other UI font settings and the frame-rate policy remain unchanged. See [iPad controls and dialogue](docs/IPAD.md#touch-and-dialogue).

## Development and distribution

```sh
make test             # Synthetic parser/policy tests and Swift input tests; no game needed
make audit-release    # Public-source allowlist, leak checks and all reachable Git history
make inspect          # Optional real-reference metadata integration check
```

| Directory | Contents |
| --- | --- |
| `tools/`, `tools/disco_port/` | Build entry points and inspection/validation modules |
| `runtime/UnityHost/` | Original iOS, display, memory and controller adapters |
| `runtime/AndroidHost/`, `apps/android/` | Original Android compatibility layer, touch overlay and diagnostic probe |
| `runtime/InputCore/`, `apps/ipad/` | Separate touch-input diagnostic, not the game |
| `tests/` | Synthetic fixtures; no game data |
| `reference/`, `artifacts/` | Private local inputs and outputs, excluded from Git |

[Release policy](docs/RELEASE.md) defines what can be published and the remaining rights review. MIT covers this repository's original work only; it grants no rights to the game, Unity, or supplied plugins. A source-only audit does not establish legal clearance. This project is not affiliated with or endorsed by their owners.

Detailed engineering evidence: [status](docs/STATUS.md), [native integration](docs/NATIVE.md), [memory](docs/MEMORY.md). Earlier [geometry diagnostics](docs/UNITY.md) are retained for investigation and are separate from the playable build.
