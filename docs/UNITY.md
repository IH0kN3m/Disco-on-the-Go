# Unity diagnostic

Requires Unity **2020.3.12f1**, iOS Build Support, a valid Unity license, Rosetta for the Intel editor, and Xcode. The diagnostic uses recovered static geometry, neutral materials, and a new camera. It contains no executable game methods or original shaders.

```sh
make setup-unity       # Official archived packages, approximately 4.2 GB download
make stage-unity       # Requires successful scene 6 recovery
make export-unity-ios
make build-unity-ipad  # Unsigned ARM64 build
make deploy-unity-ipad # Uses ignored artifacts/local-ipad.json
```

`setup-unity` verifies pinned SHA-256 hashes and unpacks packages under `artifacts/toolchains/` without running installer scripts. Editor and module bytes matched Unity's HTTPS manifest sizes and MD5 hashes during the initial download. Local `pkgutil`/`codesign` checks reported invalid legacy package/application signatures; the cause remains unresolved. No signing checks were disabled. The existing local Unity license allowed export.

To use your own installation instead:

```sh
python3 tools/build_unity.py --editor '/path/to/Unity.app/Contents/MacOS/Unity'
```

The staged project stays under `artifacts/recovered-unity/`. `staging.json` records source hashes, omissions, and diagnostic scope. Scene 6 currently stages 373 transform nodes, 67 meshes, and 82 selected mesh instances; 16 Unity built-in mesh references are omitted. Selected mesh-bearing nodes and their ancestors are enabled for diagnostic viewing because the serialized scene saves its render groups inactive. Default viewing layers 0 and 8 omit the supplied build’s FOW/Hidden layers; null-material and shadowcaster-only renderers are also omitted. `--layers` selects a different diagnostic layer set. This overrides saved activation flags; it does not recover the game’s activation behavior. Original materials, textures, lights, cameras, colliders, animation, navigation, audio, gameplay, and Unity touch navigation remain pending.

Xcode export stays under `artifacts/build/unity-ios/`. The export adapter removes four obsolete `-mno-thumb` flags, disables bitcode, and connects Unity startup and activation callbacks to one `UIWindowScene`. Unsupported trampoline/project layouts fail explicitly. Without this scene adapter, the iPadOS 27 startup report traps in `UIApplicationEvaluateRuntimeIssueForNoSceneLifecycleAdoption` before geometry initialization. The adapter supports one full-screen diagnostic window; resizing, multiple windows, and lifecycle edge cases still require testing.

Unsigned products are under `artifacts/build/unity-device/`; signed products under `artifacts/build/signed-unity/`. Deployment logs, crash reports, and device identifiers stay under `artifacts/deployment-unity/`. A returned process identifier alone does not establish a working renderer. `Documents/geometry-startup.log` in the app container records initialization, viewport/bounds, and errors; `Documents/geometry-frame.png` captures a frame after the Unity splash finishes; keep retrieved copies under ignored artifacts. The initial black screen was traced to a stripped shader referenced only by runtime name; the scene now serializes its diagnostic material/font references so the build retains them.

References: [pinned Unity release](https://unity.com/releases/editor/whats-new/2020.3.12f1), [official package manifest](https://download.unity3d.com/download_unity/b3b2c6512326/unity-2020.3.12f1-osx.ini), [Apple scene lifecycle migration](https://developer.apple.com/documentation/technotes/tn3187-migrating-to-the-uikit-scene-based-life-cycle).

Device results on 7 October 2026: lifecycle bridge stopped the startup trap; explicit material references resolved the stripped-shader error; diagnostic activation reached 103 renderers. The user confirmed visible geometry but reported an incorrect view with helper geometry included. The focused selection reduces this to 82 renderers. Subsequent distortion reports led to preserved source normals, precise vertex bounds, corrected diagnostic lighting, and a capture after the splash. The retrieved M4 frame confirms rendered geometry and legible UI; original visual fidelity remains unverified.
