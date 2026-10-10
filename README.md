# Disco on the Go

Build and play Disco Elysium locally on iPad and Android using your own macOS `Disco.app`.

This unofficial project contains build tools and compatibility code. It does not include the game, its icon, extracted assets, Unity or ready-to-install packages. The app icon is taken from your game during the build.

## Tested devices

| Device | Confirmed |
| --- | --- |
| iPad Pro M4, 13-inch, 16 GB | Gameplay, dialogue, touch movement, pinch zoom, virtual controller, saving/loading and scene transitions |
| Galaxy Tab S10 Ultra | Gameplay, dialogue, outdoor rendering, touch controls and two-finger object highlighting |
| Retroid Pocket 5 | Opening dialogue, room rendering and quick-save |

A complete playthrough has not been verified. Other devices need testing; see [compatibility and known limits](docs/COMPATIBILITY.md).

## Before building

Use an Apple silicon Mac with Python 3.11+, Rosetta and at least 60 GiB free after tool installation. Put your game at `reference/Disco.app`; a symlink to your existing copy also works. The tools require one specific Unity 2020.3.12f1 game revision and reject other inputs. [Input and tool requirements](docs/BUILD.md) explain the checks.

For iPad, install and select Xcode 27.x. For Android, install JDK 17 and Android SDK Command-line Tools and accept the SDK licenses; see [Android setup](docs/ANDROID.md).

## Build

```sh
make setup        # Downloads pinned tools and Python dependencies
make doctor       # Checks the game revision and tools
make port         # Builds the unsigned iPad app
```

Unity 2020.3.12f1 needs a valid license. If activation is required, open the locally installed editor before running `make port`.

For Android, use:

```sh
make setup PLATFORM=android
make doctor PLATFORM=android
make port PLATFORM=android
```

Builds run offline once setup and license activation are complete. They read the original game without modifying or launching it on the Mac. No Windows game, scene recovery or decompiler is needed.

| Output | Location |
| --- | --- |
| Unsigned iPad app | `artifacts/build/native-engine-device-persistent/Build/Products/Debug-iphoneos/Disco on the Go.app` |
| Android APK | `artifacts/android/build-game/disco-on-the-go.apk` |
| Android core data | `artifacts/android/build-game/main.1.org.discoport.androidgame.obb` |
| Android streaming data | `artifacts/android/game-data/external/GameFiles/` |

The APK alone is not the complete game. Installation transfers its core and streaming data too. Generated files and build logs stay under ignored `artifacts/`.

## Install

Save before updating. Keep the same application identifier and Android signing key to preserve update compatibility and saves. Both platforms need about 10 GB for game data, plus installation space and saves.

**iPad:** use a paired, unlocked device with Developer Mode enabled and an authorized Apple development team with the requested memory capabilities. The tested setup uses a paid account. Create the private configuration described in [iPad installation](docs/IPAD.md), then:

```sh
make install
```

**Android:** enable USB debugging and authorize the Mac over USB or paired Wi-Fi. With one connected device:

```sh
make install PLATFORM=android
```

The installer signs/installs the app, transfers assets and launches it. Initial transfers are large; later installs reuse matching data. For multiple devices, choose one in `artifacts/local-android.json` as described in [Android installation](docs/ANDROID.md#install).

## Controls

Tap to move and interact. Tap the gamepad icon to show or hide the virtual controller; drag the icon itself to reposition it. Physical controllers are also supported by the game's input system.

On iPad, pinch to zoom and hold to highlight objects. Android uses a two-finger hold for highlighting; pinch zoom is disabled. The iPad dialogue-size presets are slightly larger for readability.

## Contributing

```sh
make test
make audit-release
```

Tests use synthetic data and do not require the game. Public CI runs source checks only. For a bug report, include the device/GPU, game fingerprint, build step and reproduction steps. Keep game files, signing keys, device identifiers and unreviewed logs private.

[Build troubleshooting](docs/BUILD.md) · [Current validation](docs/STATUS.md) · [Release policy](docs/RELEASE.md)

MIT applies to this project's original code only. Game, Unity and plugin licenses remain separate. This project is not affiliated with or endorsed by their owners. Do not distribute your generated game builds through this repository.
