# Disco iPad port

Native iPad Pro M4 port investigation, built locally from a supplied macOS `Disco.app`.

The original ARM64 game runs with Unity 2020.3.12f1’s iOS engine on a stock 13-inch M4 iPad. Opening dialogue, textured gameplay, tap movement, pinch zoom, virtual-controller input, saving, area transitions, and full 4:3 landscape framing have been verified on the device. Complete-game stability and bounded memory across long sessions remain pending. Separate touch and geometry diagnostics are also retained.

## Required now

- Mac with Xcode and its command-line tools selected.
- Python 3.11 or newer. Tested with Python 3.14.7 and Xcode 27.0.
- Original Unity 2020.3.12f1 build at `reference/Disco.app`.
- For device execution: Apple developer account, signing team, and connected iPad with Developer Mode enabled.

## Commands

```sh
make inspect
python3 tools/methods.py SaveGame --image Assembly-CSharp.dll
make setup-scenes
make scenes
make recover-scene
make recover-vtc
make setup-unity
make stage-unity
make export-unity-ios
make build-unity-ipad
make test
make build-ipad
make deploy-ipad    # Requires artifacts/local-ipad.json; see docs/IPAD.md
make prepare-runtime-probe
make deploy-runtime-probe
```

`BUNDLE=/absolute/path/Disco.app` overrides the reference path for inspection commands. Generated data, dependencies, and builds stay ignored by Git.

| Path | Purpose |
| --- | --- |
| `tools/disco_port/` | Mach-O, IL2CPP metadata, and method indexing |
| `tools/inspect_scenes.py` | Scene inventory and selected built-in component export |
| `tools/recover_scene.py` | Script values, owned asset references, meshes, materials, and standard textures |
| `tools/inspect_vtc.py` | Bounded virtual texture container validation and page samples |
| `runtime/UnityHost/` | Original iOS runtime adapters, input controls and geometry diagnostic |
| `runtime/InputCore/` | Touch actions and viewport coordinate conversion |
| `apps/ipad/` | Buildable UIKit input harness |
| `tests/`, `runtime/InputCoreTests/` | Parser and input tests using synthetic fixtures |
| `reference/` | User-supplied game, never committed |
| `artifacts/` | Local indexes, scene exports, logs, and builds |

Device setup is in [docs/IPAD.md](docs/IPAD.md). Tool formats and limits are in [docs/TOOLING.md](docs/TOOLING.md).

Unity setup and diagnostic build requirements are in [docs/UNITY.md](docs/UNITY.md). The inspection, UIKit, and native CPU probe targets do not require Unity. Native probe results and limits are in [docs/NATIVE.md](docs/NATIVE.md).

Original-game build commands and verified device results are in [docs/NATIVE.md](docs/NATIVE.md). Memory findings and native BC integration are in [docs/MEMORY.md](docs/MEMORY.md). Next: state-safe memory bounds and longer-play verification.

Only original tooling and host code belong in this repository. Game assets, recovered game code, method databases, and signing material remain local. The MIT license applies to this repository's original code.
