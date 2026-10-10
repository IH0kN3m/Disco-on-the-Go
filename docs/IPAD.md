# iPad installation

1. Build with `make port`.
2. Pair the iPad with Xcode, enable Developer Mode, trust the Mac and leave it unlocked. USB or an already paired local-network connection works.
3. Sign in to your authorized Apple development team in Xcode. It needs Certificates, Identifiers & Profiles access, device registration and the increased-memory/extended-address-space capabilities requested by the app. The verified setup uses a paid account.
4. Create the ignored `artifacts/local-ipad.json`:

```json
{"team_id":"YOURTEAMID","device_identifier":"YOUR-PAIRED-DEVICE-ID","bundle_id":"org.yourname.discoonthego"}
```

Choose a unique identifier available to your team. Existing installations must retain their current identifier to keep their app container and saves. Omitting it preserves the project's historical identifier. Find your paired device with `xcrun devicectl list devices`; keep the configuration and command output private.

```sh
make install
```

Installation verifies a physical iPad on iPadOS 17+, signs the app, transfers its checked asset tree and launches. The first transfer is about 9.6 GB. Later installs skip matching assets. The signed app is under `artifacts/build/signed-engine-persistent/Build/Products/Debug-iphoneos/Disco on the Go.app`.

Save before updating. Back up the app's Documents/SaveGames and Documents/Settings before deleting or replacing its container. Do not change the bundle ID during a playthrough. Development profiles expire; renew signing before travel. Requested memory entitlements do not grant access to all installed RAM.

## Touch and dialogue

Tap to move/interact, pinch to zoom and hold to highlight. The gamepad icon toggles the virtual controller. Drag the icon itself to move it without toggling; its saved position stays inside the display's safe area. Hiding the pad releases its inputs and restores direct touch.

The landscape world and UI fit the actual display aspect, including dialogue canvases created after loading. Dialogue font presets are increased by 12.5%, rounded to whole font units, while retaining the selected setting. Wrapping and scrolling use the game's existing code. The M4 user confirmed the layout, controller dragging and increased text size.

Native Metal BC texture support and sufficient memory are required; unsupported GPUs stop before loading game textures. Other iPads need device testing. See [compatibility](COMPATIBILITY.md).

Runtime logs are written to Documents/native-engine.log. Retrieve them only into ignored artifacts. After runtime changes, verify save loading, conversation layout, movement, controls, a scene transition and save/reload on the actual device.
