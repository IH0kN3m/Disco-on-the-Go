# Disco on the Go

Build and play Disco Elysium locally on iPad or Android from your own macOS `Disco.app` (GOG version). This unofficial project includes tools and compatibility code; game files and the app icon come from your copy.

## Requirements

- Apple silicon Mac, Python 3.11+, Rosetta and 60 GiB free after installing tools.
- Put the game at `reference/Disco.app`, or symlink it there. Only the [pinned ARM64 revision](tools/disco_port/build_inputs.py) is supported; `make doctor` checks it.
- Unity 2020.3.12f1 with a valid license. Setup downloads the editor; its executable path is in `artifacts/toolchains/unity-editor-path.txt`. Open the enclosing Unity.app to activate it.
- [iPad: Xcode and signing setup](docs/IPAD.md) · [Android: JDK and SDK setup](docs/ANDROID.md).
- About 10 GB on the device, plus room for installation and saves.

## Build

Run from the repository directory:

```sh
make setup
make doctor
make port
```

For Android, add `PLATFORM=android` to each command. Setup downloads tools; builds run offline afterward and leave the original game unchanged. Windows files are unnecessary.

Install using the [iPad](docs/IPAD.md) or [Android](docs/ANDROID.md) instructions. The installer transfers the app and game data. Save before updating; uninstalling deletes saves.

If a build fails, follow the reported log path. For missing tools, rerun setup; for Unity export failures, check licensing and Rosetta. Generated files and logs stay in `artifacts/`.

## Controls

Tap to move or interact. Tap the gamepad icon to show/hide the controller; drag the icon to reposition it. Physical controllers use the game's controls.

- **iPad:** pinch to zoom, hold to highlight objects.
- **Android:** hold two fingers to highlight. Pinch zoom is disabled.

## Known limits

[Tested devices and current results](docs/STATUS.md). Other models and a full playthrough are unverified. Visited scenes stay cached, so long sessions may exhaust memory. Save often.

MIT covers this project's original code only; game and tool licenses remain separate. Do not upload game files, generated builds, signing keys or private logs. Contributors: `make test` and [release checks](docs/RELEASE.md).
