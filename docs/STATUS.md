# Validation status

10 October 2026

## Device results

- **iPad Pro M4, 13-inch, 16 GB:** opening dialogue, textured gameplay, touch movement, saving/loading, scene transitions, landscape fitting, pinch zoom and virtual controller confirmed. The latest dialogue layout, draggable gamepad icon and larger dialogue text are user-confirmed.
- **Galaxy Tab S10 Ultra:** menus, dialogue, room/outdoor rendering and two-finger highlighting confirmed. Mali outline rendering is fixed. The draggable controller icon's tap/drag behavior was captured on device.
- **Retroid Pocket 5:** opening dialogue/room rendering and quick-save confirmed after the ARM64 instruction fix. The latest Mali-specific workaround has not been retested on this disconnected handheld.

Full playthrough, later-area coverage, background/resume and sustained memory/performance remain unverified. See [compatibility](COMPATIBILITY.md).

## Source and build checks

The release cleanup removes the early Swift touch harness, recovered-geometry pipeline, Windows comparison tools, standalone capability probes and their unused tests. The shipping runtime/input/parser tests remain. Both apps are named **Disco on the Go**; icons are derived from the local game during builds and never tracked. Stable app identifiers and signing-key paths are retained for updates.

The current suite passes 105 synthetic tests. iPad startup diagnostics, periodic memory scans and screenshot probes were removed; GPU capability gating, memory-warning handling, full texture quality, display/input and scene adapters remain. Production Android rendering and exception/unwind adapters remain.

The complete branded iPad pipeline passed all 13 steps with the source game unchanged. Its app name, executable and packaged icon were verified. The development-signed app was installed over the existing M4 container after backing up saves/settings; the asset manifest matched, and the device log confirms engine startup, dialogue presets, touch controls and the full landscape profile. Gameplay in this newly trimmed host has not been separately user-tested.

The complete branded Android pipeline passed all five steps with the source game unchanged. APK launcher name and icon pixel equality were checked. The APK, OBB and streaming data are ready locally; this branded Android build has not been installed on a device. Object preservation passed for 1,953 containers and 202 copied files; all 5399 unique shader pairs compiled and linked without errors. The source and reachable-history audit has no findings; it is rerun after the release-preparation commit. Fresh first-time tool download/license activation on another Mac is not established.

No GitHub push, public upload or generated-game release has been performed.
