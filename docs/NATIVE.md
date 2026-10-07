# Native runtime probe

For the current end-to-end build use [BUILD.md](BUILD.md) and `make port`. The commands and results below document the incremental native experiments; they are not additional prerequisites.

The supplied ARM64 GameAssembly exports 232 IL2CPP entry points and imports 334 symbols. The CPU probe derives an iOS framework from that module, preserves its executable sections byte for byte, and uses the original metadata. No reference binary is loaded on the Mac or changed in place.

```sh
make prepare-runtime-probe
make deploy-runtime-probe
```

Requires Xcode, the supplied app, and the existing ignored `artifacts/local-ipad.json` device/team configuration. Unity editor installation is not required for this CPU check. Preparation validates Mach-O bounds, dynamic-library type, build platform, dependency paths, executable address/offset ownership, metadata v27, and output code hashes. It removes the derived copy's old signature, sets its iOS loader platform, rewrites the three versioned Apple framework paths, and changes its install name. Xcode development-signs the embedded framework and app. Only the explicitly enabled device build includes game bytes; normal touch-harness builds skip them. Prepared module/metadata hashes are checked before embedding.

Actual result on 7 October 2026: the physical stock 13-inch M4 loaded the derived module, initialized the original IL2CPP runtime/metadata, resolved `UnityEngine.Vector3.Dot` through the original runtime API, and invoked it with `(1,2,3)` and `(4,5,6)`. The boxed result was **32**. Log: `Documents/native-runtime.log` in the `org.discoport.runtimeprobe` app container; retrieved output stays under `artifacts/runtime-probe/`.

This proves this native CPU/runtime check. It does not establish game-specific method behavior, plugin compatibility, asset/shader compatibility, touch integration, or gameplay. The probe keeps the runtime loaded for the process lifetime and does not start the game.

Static follow-up: the exported Unity 2020.3.12f1 iOS engine archive references 161 unique IL2CPP C APIs; the original module exports all 161. Its additional `Unity_il2cppNoExceptions` reference is supplied by the generated player options source. This checks symbol coverage only. The exported diagnostic currently registers a stripped subset of Unity bindings and links its own `libil2cpp.a`; an engine experiment must select one runtime provider, use matching metadata, and establish the required bindings before gameplay can be assessed. The audit listings remain under `artifacts/linkage/`.

## Original game startup experiment

Requirements: pinned Unity 2020.3.12f1 iOS export, prepared CPU-probe inputs, pinned UnityPy, Xcode, and the ignored device/team configuration. Run in order:

```sh
make prepare-runtime-probe
make prepare-native-plugins
make prepare-amplify-plugin
python3 tools/prepare_engine_probe.py --game-data --retag-serialized
make retag-startup-bundles
make retag-addressable-bundles
python3 tools/configure_engine_assets.py --increased-memory --no-debug-memory --amplify-cpu --lazy-scenes --landscape
make enable-engine-bc
make deploy-engine-probe
```

Each staging run replaces the derived data tree and engine archive; rerun both bundle commands and asset configuration afterward. `make prepare-engine-probe` instead stages the earlier diagnostic data. `make build-engine-ipad` builds the current staged experiment unsigned. Persistent mode keeps the roughly 9.6 GB Data tree in `Documents/DiscoPortAssets`; the signed app is about 96 MB. Deployment fingerprints all staged files, uploads data and its readiness marker once, then skips matching uploads on subsequent builds. The host checks the expected marker and required settings before startup. The marker attests completed deployment; it does not rehash device files at every launch. Read `Documents/native-engine.log` from the `org.discoport.engineprobe` app container after launch. Device logs and GPU captures belong under `artifacts/deployment-engine/`.

`python3 tools/deploy_ipad.py --engine --mip-limit 0` explicitly requests full-resolution diagnostic textures. Values 1–3 reduce resolution for experiments only. CoreDevice options must precede the bundle identifier; the launch helper now validates actual restart/environment settings in returned JSON. Earlier after-identifier flags became game arguments, so those runs did not establish the requested mip or debugger settings.

Optional `tools/configure_engine_assets.py --debug-memory` also requests development-only debugging memory and extended addressing. Capabilities persist in the staged project; fresh preparation removes that configuration. M4 process budget remains about 6 GiB with or without debugging memory. Lazy scene loading and Amplify CPU integration resolve the opening crash; longer-session bounds remain pending. Memory and BC integration are documented in [MEMORY.md](MEMORY.md).

`make enable-engine-bc` validates the exact 2020.3.12f1 Metal object, derives renamed implementations from its embedded bitcode, and links original wrappers for format mapping, block sizes, capability flags and texture-view compatibility. It gates BC on the actual engine Metal device. Generated engine code stays under ignored artifacts; GameAssembly and asset bytes remain unchanged. Fresh staging requires rerunning this step.

The original GameAssembly replaces the generated `libil2cpp.a`; 104 diagnostic generated managed sources are excluded. Generated glue registers 8,163 iOS engine bindings and all 62 available engine modules/classes. Prepared module, metadata, and Steam library hashes are checked. The reference remains unchanged, and its binaries are never loaded on the Mac.

The preparation changes only the platform field in 76 derived Unity serialized files from macOS (2) to iOS (9). It validates v22 headers, Unity version, byte order, metadata/file/data boundaries, and type-tree flags. Fifty startup and 1,827 addressable UnityFS v7 containers receive the same loader-platform change; every object's raw body and every resource child's bytes are verified unchanged after saving. This does not convert shader programs or texture/audio payloads. Generated reports record source/derived hashes.

Streaming assets move to the iOS `Data/Raw` directory, and `AssetBundles/OSX` becomes `AssetBundles/iOS`. Virtual textures move to `Data/Resources/Data/AmplifyTexture`, the path requested by the compiled desktop game. The exported iOS default resources are supplied. The host checks for the absent desktop-metadata `AudioSettings.Mobile.InvokeOnMuteStateChanged` method before forwarding iOS mute notifications; the earlier unguarded call crashed.

The supplied ARM64 Steam library is derived with validated loader/dependencies and unchanged executable sections, then embedded and development-signed. The host maps only `steam_api` to it. On the physical M4 the library loaded; Steam client initialization failed because no client was running, and original game code continued with achievement provider “NONE.” Galaxy glue remains unavailable.

Actual device results on 7 October 2026:

- Original runtime/metadata and iOS engine initialized; Metal reported Apple M4. Original `Time` methods reached live engine state; frames advanced from 64 at 2.175 seconds to 127 at 4.275 seconds.
- Original startup scripts ran localization, MEDIUM profile selection, settings, game-data loading, intro sequencing, achievement initialization, and area loading.
- The original dialogue build bundle loaded after addressable retagging. Church interior and Whirling floors 1/2 began loading; the engine reported roughly 66,000 loaded objects.
- A GPU screenshot contains the original copyright notice and loading indicator. The latest 30/60-second GPU captures confirm the original main menu; original runtime frames reach 3,114 at 60.633 seconds. Layout/orientation is incorrect. Story gameplay is not verified. Corrected debugger launch/attachment now captures `EXC_RESOURCE`: the app exceeds a 6,144 MB memory watermark during new-game loading. The user reproduced New Game → Thinker → Continue; a second captured main-thread stack runs through scene loading into `System.GC::Collect`. These are stop locations, not dominant-allocation attribution.
- The stock backend triggered DXT decompression warnings. The experimental BC bridge eliminates them, reports BC support through original SystemInfo, and reaches Lobby/Whirling floor 2 loading, but still exceeds the memory limit. The corrected directory was installed in a subsequent run: virtual-texture DirectoryNotFoundException errors disappeared, while the loading memory warning remained.

The subsequent lazy-loading + Amplify CPU checkpoint runs original opening dialogue, renders the textured Whirling floor 2 room, and accepts tap-to-move, confirmed by the user on the M4. The initial room holds near 4.0 GiB. The host keeps 2 scenes at the menu instead of 33; missing world scenes are loaded additively and registered before the original transition resumes. `--lazy-scenes` in asset configuration persists this selection for Home Screen launches; the deployment environment flag alone only applies to that launch. Visited scenes remain cached; no state-safe eviction is implemented yet.

`make prepare-amplify-plugin` derives the supplied CPU codec framework with unchanged executable sections. Its only unsupported dependency, desktop OpenGL, is replaced with a separately built explicit failure guard. The host maps `AmplifyTextureNative` to the embedded framework and validates its required codec exports. Desktop GPU calls abort with their name rather than return fabricated results. No such calls were observed in the verified opening room. All binaries, generated listings and hashes remain under artifacts. The preparation must be run before `--amplify-cpu` configuration.

`--landscape` requests a fixed landscape orientation using the pinned engine bindings and modern window-scene geometry API. The exported controller transition sets Unity's controller pointer before UIKit queries the supported orientation mask. The device reports a 2752×2064 backbuffer. The game display adapter sets its camera/input aspect to the actual 4:3 viewport and normalizes its canvas/reference dimensions. It reapplies the profile after scene changes. The user confirms full-screen gameplay and aligned bottom-bar controls; reverse-landscape rotation is not yet implemented. `--no-landscape` disables this selection.

The same selection enables pinch zoom and a hidden virtual controller, shown with a small gamepad icon near the upper-right edge. Pinch invokes the original zoom-factor setter and clamp, preserving its area limits and camera curves; camera changes and locks cancel the gesture. The custom layout has dual sticks, a D-pad, ABXY, shoulders and triggers. It uses [Apple's GCVirtualController](https://developer.apple.com/documentation/gamecontroller/gcvirtualcontroller) with a custom interface and feeds the existing iOS engine's GameController reader. Its Menu button injects Escape. Hiding disconnects the controller; hide/suspend resets held buttons and sticks. Gaps between controls pass touches to Unity. The device reports one Unity joystick and original InControl selecting **Apple MFi Controller**. The user confirms controller movement, A/B interaction, hiding the pad and pinch zoom work. Input ownership tests and the unsigned engine build pass. The verified game UI scale is unchanged.

The user reports saving and scene transitions work; a subsequent GPU frame shows Harry and Kim outside. Remaining integration: full visual fidelity, state-safe memory bounds, startup exceptions, desktop services and long-session/save-state coverage. The supplied plugin's OpenGL path requires implementation if encountered. The complete game is not yet verified.

Never commit derived frameworks, game data/metadata, generated glue, export/import listings, signing material, device identifiers, or logs. The repository contains only original preparation, host, and validation code.
