# Building Disco on the Go

## Game input

Place your macOS game at `reference/Disco.app`, or symlink that path to your copy. The current compatibility layer requires the inspected Unity 2020.3.12f1 ARM64 revision. `make doctor` verifies GameAssembly, metadata, Steam and Amplify fingerprints in `tools/disco_port/build_inputs.py`.

The required GameAssembly SHA-256 is:

```text
0550f5a1e9fb9addba0b365908f21bc5a04a2f3979f1b2a640774a05a6c7ab52
```

A storefront/version label is insufficient. Other revisions need reviewed compatibility support; do not bypass the checks. The reference stays read-only. The full build compares its complete file fingerprint before and after processing.

## Setup

Use macOS on Apple silicon, Python 3.11+, Rosetta and 60 GiB of free space after installing tools. iPad builds require Xcode 27.x with first-run setup complete. Android's additional prerequisites are in [ANDROID.md](ANDROID.md).

`make setup` creates `.venv`, installs `requirements.lock`, and downloads checksum-pinned Unity 2020.3.12f1 and iOS support into `artifacts/toolchains/`. `make setup PLATFORM=android` also installs the Android module, legacy export SDK/NDK/JDK and the shader compiler. Modern Android SDK packages are installed using your SDK's `sdkmanager`.

Setup does not activate Unity or supply a license. `artifacts/toolchains/unity-editor-path.txt` records the editor executable; open its enclosing Unity.app if activation is needed. An existing exact-version editor with the required modules can be selected by replacing that file with its absolute executable path. Android module setup only modifies the locally extracted editor.

Archived Unity packages had legacy-signature issues on the test Mac. The build does not bypass system security checks. If macOS rejects the editor, resolve its installation with Unity's supported tooling.

## Build and rebuild

```sh
make doctor
make port
# Or:
make doctor PLATFORM=android
make port PLATFORM=android
```

`make port` exports an empty Unity host, derives the runtime and assets from your game, applies the platform adapters, derives the app icons and builds the final app. Android also audits derived object preservation. Builds do not download tools, sign iPad apps or access devices. One build owns the workspace at a time.

A full build regenerates the pipeline. For code-only iteration after a successful build, use `make build-ipad` or `make build-android`; these reuse staged game assets. `make audit-android` validates the staged Android assets and shader pairs.

Step logs and input/output fingerprints are in `artifacts/reproducibility/<timestamp>/`. `python3 tools/port.py plan --platform ipad` or `--platform android` prints the commands. Failures stop the build and identify the relevant log. Fix the cause and rerun.

Generated projects, icons, data and packages remain under `artifacts/`. Keep the original game and local signing keys for future updates. Rebuilding is repeatable from checked inputs; signed binaries are not promised to be byte-identical.

## Troubleshooting

- **Unsupported game revision:** use the matching input or implement separately reviewed support for yours.
- **Missing tools:** run setup for the selected platform. `make doctor` checks pinned versions; Unity license validation happens when the editor runs.
- **Unity export fails:** inspect the private editor/process logs. Check the editor version, modules, Rosetta and licensing.
- **iPad signing fails:** check the selected Xcode team, Certificates/Identifiers/Profiles access, device registration and memory capabilities.
- **Missing/stale game data:** run `make install` for the appropriate platform; keep the app identifier consistent.
- **App stops while loading:** record the device/GPU and reproduction steps. Inspect private runtime logs; avoid posting credentials, device IDs or game data.

Compilation, static audits and launch submission are separate from device gameplay validation. See [STATUS.md](STATUS.md).
