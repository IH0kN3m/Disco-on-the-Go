# iPad

Requires Xcode 27.x with first-run setup complete, iPadOS 17+, native Metal BC texture support and sufficient memory. The verified device is the 16 GB iPad Pro M4; its process limit was about 6 GiB.

1. Pair the iPad with Xcode, enable Developer Mode, trust the Mac and unlock it.
2. Sign into your Apple development team in Xcode. The tested setup uses a paid account with Certificates, Identifiers & Profiles access, device registration and increased-memory/extended-address-space capabilities.
3. Find the device with `xcrun devicectl list devices`. Create `artifacts/local-ipad.json`:

```json
{"team_id":"YOURTEAMID","device_identifier":"YOUR-PAIRED-DEVICE-ID","bundle_id":"org.yourname.discoonthego"}
```

Choose an identifier available to your team; keep it unchanged for updates and saves.

After building:

```sh
make install
```

This signs, transfers and launches the game. Initial asset transfer is about 9.6 GB; later installs reuse matching data. Development signing expires: renew it before travel. Back up Documents/SaveGames and Documents/Settings before removing the app.
