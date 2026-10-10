# Android build and installation

The Android build uses the same macOS `Disco.app` as iPad. Windows files are not required.

## Setup

Use an Apple silicon Mac with Python 3.11+, Rosetta, JDK 17 and Android SDK Command-line Tools (latest). `ANDROID_HOME` selects the SDK; the default is `$HOME/Library/Android/sdk`. Accept its licenses before setup:

```sh
export JAVA_HOME="$(/usr/libexec/java_home -v 17)"
"$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" --licenses
make setup PLATFORM=android
make doctor PLATFORM=android
make port PLATFORM=android
```

If `ANDROID_HOME` is unset, replace it in the license command with your SDK path. Setup installs platform-tools, SDK 36, build-tools 36.0.0 and NDK 27.2.12479018. Unity export uses separately downloaded checksum-pinned SDK tools 26.1.1, platform 30, build-tools 30.0.2, NDK r19 and JDK 8. APK assembly uses JDK 17 and the modern SDK without Gradle/Maven downloads.

Unity 2020.3.12f1 needs a valid license. `DISCO_ANDROID_SDK`, `DISCO_ANDROID_NDK` and `DISCO_ANDROID_JDK` override legacy export paths. See [shared input/build requirements](BUILD.md).

## Outputs

All three components are required:

| Path | Content |
| --- | --- |
| `artifacts/android/build-game/disco-on-the-go.apk` | App, runtime and metadata |
| `artifacts/android/build-game/main.1.org.discoport.androidgame.obb` | Core Unity data |
| `artifacts/android/game-data/external/GameFiles/` | Streaming and virtual-texture data |

The historical Android package ID remains stable for updates. The first build creates `artifacts/android/signing/debug.keystore`; later builds reuse it. Preserve this private key to update an existing installation. Never publish these generated packages or data.

## Install

Enable debugging and authorize the Mac over USB or paired Wi-Fi. With exactly one connected device:

```sh
make install PLATFORM=android
```

The installer records that selection in ignored `artifacts/local-android.json`. For multiple devices, create it explicitly:

```json
{"device_identifier":"YOUR-ADB-DEVICE-SELECTION"}
```

Installation verifies and transfers the APK/OBB, uploads streaming assets with ADB sync and launches the game. Save before updating: the app restarts. Uninstalling deletes saves. The first transfer is large, especially over Wi-Fi.

For an additional device, use its own private selection/report paths:

```sh
python3 tools/deploy_android_game.py --config artifacts/local-android-other.json --output artifacts/android/other-device --install-only
python3 tools/upload_android_assets.py --config artifacts/local-android-other.json --log artifacts/android/other-upload.log
python3 tools/deploy_android_game.py --config artifacts/local-android-other.json --output artifacts/android/other-device --launch-only
```

## Controls and compatibility

Tap to move/interact. Hold two fingers to highlight objects. Tap the gamepad icon to show/hide; drag it to reposition. Hiding, cancellation and focus loss release controller inputs. Pinch zoom is disabled.

ARM64, Android API 28+ and GLES 3.2 are required. Actual GPU features and memory matter; model names do not establish support. Galaxy Tab S10 Ultra and Retroid Pocket 5 are the tested baselines. The Samsung uses runtime BC decoding; supported Adreno formats retain native sampling. The Mali outline workaround is user-confirmed. Full playthrough, later scenes, background/resume and sustained performance remain unverified.

`make audit-android` checks staged object preservation and all converted shader variants. APK/native libraries are aligned for 16 KiB pages; device execution on 16 KiB pages has not been tested. Source textures retain their bytes and dimensions; static checks cannot guarantee every driver/scene's visual fidelity.

The game-specific provider maps the supplied ARM64 runtime, validates ownership and import adapters, translates three unsupported SIMD instructions and seals executable memory after staging. Unsupported calls stop with a diagnostic. This is not a general-purpose macOS compatibility layer.
