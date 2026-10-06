# Native runtime probe

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
python3 tools/prepare_engine_probe.py --game-data --retag-serialized
make retag-startup-bundles
make retag-addressable-bundles
make deploy-engine-probe
```

Each staging run replaces the derived data tree; rerun both bundle commands afterward. `make prepare-engine-probe` instead stages the earlier diagnostic data. `make build-engine-ipad` builds the current staged experiment unsigned. The full app is approximately 9.6 GB; installation permits a 15-minute timeout. Read `Documents/native-engine.log` from the `org.discoport.engineprobe` app container after launch. Device logs and GPU captures belong under `artifacts/deployment-engine/`.

The original GameAssembly replaces the generated `libil2cpp.a`; 104 diagnostic generated managed sources are excluded. Generated glue registers 8,163 iOS engine bindings and all 62 available engine modules/classes. Prepared module, metadata, and Steam library hashes are checked. The reference remains unchanged, and its binaries are never loaded on the Mac.

The preparation changes only the platform field in 76 derived Unity serialized files from macOS (2) to iOS (9). It validates v22 headers, Unity version, byte order, metadata/file/data boundaries, and type-tree flags. Fifty startup and 1,827 addressable UnityFS v7 containers receive the same loader-platform change; every object's raw body and every resource child's bytes are verified unchanged after saving. This does not convert shader programs or texture/audio payloads. Generated reports record source/derived hashes.

Streaming assets move to the iOS `Data/Raw` directory, and `AssetBundles/OSX` becomes `AssetBundles/iOS`. Virtual textures move to `Data/Resources/Data/AmplifyTexture`, the path requested by the compiled desktop game. The exported iOS default resources are supplied. The host checks for the absent desktop-metadata `AudioSettings.Mobile.InvokeOnMuteStateChanged` method before forwarding iOS mute notifications; the earlier unguarded call crashed.

The supplied ARM64 Steam library is derived with validated loader/dependencies and unchanged executable sections, then embedded and development-signed. The host maps only `steam_api` to it. On the physical M4 the library loaded; Steam client initialization failed because no client was running, and original game code continued with achievement provider “NONE.” Galaxy glue remains unavailable.

Actual device results on 7 October 2026:

- Original runtime/metadata and iOS engine initialized; Metal reported Apple M4. Original `Time` methods reached live engine state; frames advanced from 64 at 2.175 seconds to 127 at 4.275 seconds.
- Original startup scripts ran localization, MEDIUM profile selection, settings, game-data loading, intro sequencing, achievement initialization, and area loading.
- The original dialogue build bundle loaded after addressable retagging. Church interior and Whirling floors 1/2 began loading; the engine reported roughly 66,000 loaded objects.
- A GPU screenshot contains the original copyright notice and loading indicator. Main menu and story gameplay are not verified. In the corrected-path run, the process was absent after loading; no new crash report was exposed, so its termination cause remains unconfirmed. Remote debugger attachment did not complete.
- Desktop DXT textures trigger decompression warnings, and an iOS memory warning occurred during loading. The corrected directory was installed in a subsequent run: virtual-texture DirectoryNotFoundException errors disappeared, while the loading memory warning remained.

Remaining integration: virtual-texture native/GPU support, shader/texture compatibility and memory use, startup exceptions, desktop platform services, orientation, and touch gameplay. The supplied Amplify native library imports desktop OpenGL functions; it requires a separate compatibility implementation or an isolated supported path. This experiment is executing original game code, but it is not a playable port.

Never commit derived frameworks, game data/metadata, generated glue, export/import listings, signing material, device identifiers, or logs. The repository contains only original preparation, host, and validation code.
