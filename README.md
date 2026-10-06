# Disco iPad port

Native iPad Pro M4 port investigation, built locally from a supplied macOS `Disco.app`.

Current implementation: binary inspection, a searchable native method map, serialized scene/asset recovery, and a touch harness tested on a real 13-inch M4 iPad. Recovered gameplay and Unity rendering are not integrated yet.

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
make test
make build-ipad
make deploy-ipad    # Requires artifacts/local-ipad.json; see docs/IPAD.md
```

`BUNDLE=/absolute/path/Disco.app` overrides the reference path for inspection commands. Generated data, dependencies, and builds stay ignored by Git.

| Path | Purpose |
| --- | --- |
| `tools/disco_port/` | Mach-O, IL2CPP metadata, and method indexing |
| `tools/inspect_scenes.py` | Scene inventory and selected built-in component export |
| `tools/recover_scene.py` | Script values, owned asset references, meshes, materials, and standard textures |
| `runtime/InputCore/` | Touch actions and viewport coordinate conversion |
| `apps/ipad/` | Buildable UIKit input harness |
| `tests/`, `runtime/InputCoreTests/` | Parser and input tests using synthetic fixtures |
| `reference/` | User-supplied game, never committed |
| `artifacts/` | Local indexes, scene exports, logs, and builds |

Device setup is in [docs/IPAD.md](docs/IPAD.md). Tool formats and limits are in [docs/TOOLING.md](docs/TOOLING.md).

## Next dependencies

Unity **2020.3.12f1** with **iOS Build Support** is required for the Unity runtime experiment. Install through the [official version page](https://unity.com/releases/editor/whats-new/2020.3.12f1) and activate your Unity license. The current inspection and UIKit targets do not require Unity. Compatibility with current Xcode must be tested before engine integration.

Next implementation: test Amplify texture decoding and establish the gameplay-to-iOS runtime boundary. Scene values and method addresses do not provide executable game logic.

Only original tooling and host code belong in this repository. Game assets, recovered game code, method databases, and signing material remain local. The MIT license applies to this repository's original code.
