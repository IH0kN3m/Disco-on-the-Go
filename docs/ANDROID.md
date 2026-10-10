# Android

Requires ARM64, Android 9/API 28+ and GLES 3.2. Tested on Galaxy Tab S10 Ultra and Retroid Pocket 5; other devices need testing.

## Setup

Install JDK 17 and Android SDK Command-line Tools (latest). Set the SDK path and accept licenses:

```sh
export JAVA_HOME="$(/usr/libexec/java_home -v 17)"
export ANDROID_HOME="$HOME/Library/Android/sdk" # Change if installed elsewhere
export PATH="$ANDROID_HOME/platform-tools:$PATH"
"$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" --licenses
make setup PLATFORM=android
make doctor PLATFORM=android
make port PLATFORM=android
```

Setup installs the remaining SDK packages. Unity licensing is covered in the [README](../README.md#requirements).

## Install

Enable USB debugging and authorize the Mac over USB or paired Wi-Fi. With one connected device:

```sh
make install PLATFORM=android
```

For multiple devices, select one from `adb devices` in `artifacts/local-android.json`:

```json
{"device_identifier":"YOUR-ADB-DEVICE-SELECTION"}
```

Installation transfers the APK, core data and streaming assets, then launches. The first transfer is large; USB is faster. To switch devices, change the selection in that file.

The APK is `artifacts/android/build-game/disco-on-the-go.apk`; it requires the accompanying game data. Keep `artifacts/android/signing/debug.keystore` for future updates.
