# Local game reference

Place your own compatible macOS game at `reference/Disco.app`, or symlink that path to your copy. Everything here except this README is ignored. Tools statically read the app, never execute its binaries on the Mac, and write derived outputs only under `artifacts/`.

Run `make doctor` (iPad) or `make doctor PLATFORM=android` to check the exact runtime, metadata and plugin fingerprints. Other revisions require a separate compatibility audit. See [build instructions](../docs/BUILD.md). Do not upload the game or generated files with bug reports.

Optional Android comparison input: put the supplied Windows GOG setup EXE and all BIN parts in `reference/disco-win/`. Treat them as immutable. `tools/extract_windows_probe.py` extracts selected inspection files under ignored artifacts without running the installer; see [Android instructions](../docs/ANDROID.md). This comparison input is not required for either playable build; Android is built from the Mac app too.
