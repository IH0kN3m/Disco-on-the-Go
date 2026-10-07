# Local game reference

Place your own compatible macOS game at `reference/Disco.app`, or symlink that path to your copy. Everything here except this README is ignored. Tools statically read the app, never execute its binaries on the Mac, and write derived outputs only under `artifacts/`.

Run `make doctor` to check the exact runtime, metadata and plugin fingerprints. Other revisions require a separate compatibility audit. See [build instructions](../docs/BUILD.md). Do not upload the game or generated files with bug reports.
