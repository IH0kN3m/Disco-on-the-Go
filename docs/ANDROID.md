# Android port

Target: Galaxy Tab S10 Ultra, then other ARM64 devices based on measured GPU and memory capabilities. The working iPad pipeline remains separate. This is recovered gameplay, with incomplete device and game-wide validation.

## Verified status

Physical device results, 10 October 2026:

| Device | GPU / memory | Gameplay checked | Remaining checks |
| --- | --- | --- | --- |
| Galaxy Tab S10 Ultra | Mali-G720, GLES 3.2, 11.26 GiB reported RAM; no native BC sampling | Menus, loaded Whirling room, outdoor scenes, dialogue, native 16:10 layout and two-finger object outlines confirmed | Controller movement/buttons, background/resume, later scenes |
| Retroid Pocket 5 | Adreno 650, GLES 3.2, 7.52 GiB reported RAM; BC1/3/6H/7 and R16/RG16 sampling/rendering supported | Menus, opening dialogue and room; quick-save confirmed after ARM64 compatibility fix | Reload, transitions and full controller coverage; latest Mali fix not retested; currently disconnected |

- Runtime probes pass managed invocation, exception round trip, full GC, register snapshots and 16 thread suspend/resume cycles. Synthetic BC1/BC3 decode and all eight stencil bits pass the GPU probes.
- Amplify streaming uses its original CPU decoder, with GLES feedback readback and two caller-scoped framebuffer-origin adaptations. Source textures, meshes and materials retain their bytes; Samsung decompresses unsupported BC textures at runtime.
- Unsupported R16/RG16 render targets use supported R32/RG32 float storage. Supported targets retain their original formats. Device capability alone does not establish every shader or scene's fidelity.
- Static asset audit checks 1,953 serialized containers and 202 copied files, retaining original object IDs and all non-adapted object bytes. External shader references are inventoried; complete cross-file scene execution is not proven.
- All 5,399 unique staged GLES shader pairs compile and link with pinned glslang 16.6.0. macOS video decoding and an excluded desktop VR builtin advertise no supported Android subshader. Game-specific shaders are retained. Reference compilation does not prove driver execution for every variant.
- Three SHA3 `EOR3` instructions are translated to equivalent baseline SIMD XOR operations in the private Android package. The handheld's repeatable quick-save illegal-instruction crash is fixed and saving is user-confirmed.

The Android touch overlay has a draggable gamepad icon: tap to show/hide, drag to reposition. It feeds the original InControl controller API and releases inputs on hide, cancellation and focus loss. Two-finger hold feeds the game's Highlight action. Pinch zoom is removed at the user's request. Samsung captures verify icon dragging without toggling and tap-to-show/hide; the native InControl device attaches and detaches without a crash. Two-finger hold and visible object outlines are user-confirmed on Samsung. UI scale is unchanged.

The GLES bridge copies all eight stencil bits to an integer RenderTexture. On Mali, a GPU callback appended after the original outline color blit performs the palette lookup with the game's current material colors; the original edge effect remains intact. It preserves dimensions and palette values. The content-free Samsung GPU probe verifies all 256 stencil bytes and all 256 palette samples. Other GPU paths retain the original color pass; the latest bridge has not been retested on the disconnected handheld.

Frame-rate instrumentation has been removed at the user’s request; performance investigation is deferred.

Complete playthrough, all later scenes, import coverage, sustained memory/performance and suspend/resume remain unresolved. Static checks cannot guarantee absence of future glitches.

## Reproduction checked

On 10 October 2026, `make port PLATFORM=android` completed all four steps from the Mac reference, replacing the generated asset trees and compiling the APK/OBB. The complete reference bundle was unchanged. The asset audit passed for 1,953 serialized containers and 202 copied files; all 5,399 shader pairs compiled/linked with no errors. The source tests passed: 129 Python tests and four Swift input tests. The public-source and reachable-history audit had no findings.

This run reused installed licensed Unity, SDKs and the pinned Python environment. It does not establish first-time Unity activation on another Mac or a fresh-device installation. The final capture-removal rebuild was compiled and audited; the previously installed outline fix remains the user-confirmed device baseline. The iPad pipeline's default plan and tool checks remain intact.

## Inputs and source choice

Use the immutable local `reference/Disco.app` and its matching ARM64 native code, metadata and assets. Supplied binaries are inspected statically on the Mac and executed only inside the locally built Android app on the authorized device.

The supplied Windows GOG installer is retained under `reference/disco-win/`. Selected files were extracted into artifacts without executing the installer. It also contains native IL2CPP, not rebuildable managed game assemblies. The inspected Windows shaders provide the same OpenGL payloads as the Mac baseline. Its metadata and native registrations differ; do not mix the two builds.

The Android provider maps the pinned Mach-O image, checks offsets/ownership, applies validated instruction translations, rebases/import adapters and seals code RX after writable staging. Unsupported functions stop with a named diagnostic; unsupported data is inaccessible. This is a game-specific compatibility layer, not a general Mach-O loader. Remaining imports, shutdown and arbitrary game execution require further testing.

## Build requirements

- Apple silicon Mac (tested host), Python 3.11+, and Rosetta on Apple silicon for the Intel Unity editor.
- Your compatible game at `reference/Disco.app`. Exact native-module/metadata fingerprints are checked; see [input requirements](BUILD.md#game-input). No Windows files, scene recovery, decompiler or recovered Unity project are needed.
- Licensed Unity 2020.3.12f1 and its exact Android player module.
- JDK 17, Android SDK Command-line Tools, accepted SDK licenses, and at least 60 GiB free after tool installation. `ANDROID_HOME` selects the SDK; its default is `$HOME/Library/Android/sdk`.

Install JDK 17 and the SDK Command-line Tools separately, set `JAVA_HOME` to JDK 17, and use `sdkmanager` from that SDK:

```sh
sdkmanager --licenses
sdkmanager "platform-tools" "platforms;android-36" "build-tools;36.0.0" "ndk;27.2.12479018"
make setup-scenes
make setup-unity
make setup-unity-android
make setup-android-legacy
```

Setup downloads official archives separately from the game build. Legacy export tools are checksum-pinned: SDK tools 26.1.1, platform 30, build-tools 30.0.2, NDK r19 and JDK 8. The legacy setup copies platform-tools and accepted licenses from `ANDROID_HOME`. Unity licensing must already work; setup does not activate a license. `make setup-unity` also stages iOS support for the shared editor.

`DISCO_ANDROID_SDK`, `DISCO_ANDROID_NDK` and `DISCO_ANDROID_JDK` override Unity export paths. APK assembly uses JDK 17, SDK 36 and NDK 27.2.12479018 directly, without Gradle/Maven downloads.

## Build locally

```sh
make doctor PLATFORM=android
make port PLATFORM=android
```

The default `make port` still builds iPad. Android exports an empty Unity host, derives assets directly from the immutable Mac app, audits object preservation, compiles the compatibility provider and assembles a locally signed APK. It creates a private development key on first build and reuses it for updates. Keep that key and the application identifier consistent to retain update/save compatibility. The build does not contact a device or download tools.

Asset preparation replaces only its disposable generated data trees, retags 76 serialized files and 1,877 UnityFS containers, retains scene IDs, adapts Android settings and rebuilds GLES shader payloads from supplied GLCore variants. Unsupported game shader features fail explicitly. Texture dimensions and source bytes are retained. Packaging checks the complete derived inventory for missing, extra or changed files. Source bundle hashes before and after the pipeline must match.

| Private output | Purpose |
| --- | --- |
| `artifacts/android/build-game/disco-android.apk` | Runtime, metadata and first-install managed resources |
| `artifacts/android/build-game/main.1.org.discoport.androidgame.obb` | Core Unity data |
| `artifacts/android/game-data/external/GameFiles/` | Streaming and Amplify assets |
| `artifacts/reproducibility/<timestamp>/` | Tool versions, input fingerprints, per-step logs and product hashes |
| `artifacts/android/signing/` | Local development key; never publish |

The APK alone is not the complete game. All three payloads are required. Native-only iteration can use `make build-android-game` and reuse an unchanged OBB. Build timestamps, paths and local signing mean output is not promised to be byte-identical. A rebuild does not establish device execution.

## Install

Enable Android debugging and authorize the Mac over USB or paired Wi-Fi. Put your selection in ignored `artifacts/local-android.json`:

```json
{"device_identifier": "YOUR-ADB-DEVICE-SELECTION"}
```

```sh
make deploy-android-game
```

Deployment installs the APK/OBB first, uploads streaming assets, then launches. APK/OBB hashes are verified; streaming uses ADB sync. Initial transfer is large. Updates restart the game: save first. Uninstalling removes app saves. APK/native libraries are aligned for 16 KiB pages; only 4 KiB device execution has been tested.

For a different tablet, create its own ignored selection and reports. Run the content-free GPU/capability probe before claiming support; ARM64, GLES 3.2 and required CPU/GPU features are checked by the runtime, and adequate memory/storage still need device testing. Model names alone do not establish compatibility.

```sh
python3 tools/deploy_android_game.py --config artifacts/local-android-other.json --output artifacts/android/other-device --install-only
python3 tools/upload_android_assets.py --config artifacts/local-android-other.json --log artifacts/android/other-upload.log
python3 tools/deploy_android_game.py --config artifacts/local-android-other.json --output artifacts/android/other-device --launch-only
```

Keep reports private. Process survival is not proof of gameplay; check runtime logs and rendered output.

## Diagnostics and checks

```sh
make test
make inspect
make audit-release
make build-android-probe          # Content-free GPU/capability checks
make deploy-android-probe
make build-android-runtime-probe  # Private original-runtime checks
make deploy-android-runtime-probe
make inspect-android-runtime     # Static input audit
make inspect-android-initializers
make setup-glslang               # Pinned reference shader compiler
make audit-android               # All staged asset and shader checks
```

Keep recovered code, shaders, native images, metadata, assets, device identifiers, signing keys and unreviewed logs out of Git and public releases. Publish original tooling only after source/history audit and authorship review; locally generated game APKs and OBBs must not be distributed with the repository.

ABI references: [Android ARM64](https://developer.android.com/ndk/guides/abis), [Apple ARM64](https://developer.apple.com/documentation/xcode/writing-arm64-code-for-apple-platforms). Graphics references: [S3TC](https://registry.khronos.org/OpenGL/extensions/EXT/EXT_texture_compression_s3tc.txt), [GLES 3.1 uniform locations](https://registry.khronos.org/OpenGL/specs/es/3.1/GLSL_ES_Specification_3.10.pdf), [Unity shader platform IDs](https://github.com/Unity-Technologies/UnityCsReference/blob/2020.3/Editor/Mono/Graphics/ShaderCompilerData.cs), [Android page sizes](https://developer.android.com/guide/practices/page-sizes).
