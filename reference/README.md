# Local game input

Place your own compatible macOS game at `reference/Disco.app`, or symlink that path to your copy. Everything here except this README is ignored. The build reads the game without modifying or launching it on the Mac, and writes derived files only under `artifacts/`.

Run `make doctor` or `make doctor PLATFORM=android` to check exact runtime, metadata and plugin fingerprints. See [build requirements](../docs/BUILD.md). Do not upload game files or generated products with bug reports.

Any existing Windows installer comparison files under `reference/disco-win/` remain private and immutable; neither final build uses them.
