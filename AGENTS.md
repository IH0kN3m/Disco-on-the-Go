# Project conventions

Target the complete game running locally on iPads with touch input, retaining the verified iPad Pro M4 baseline. Gate compatibility by actual GPU/memory capabilities and distinguish tested devices from untested models. Begin with stock iPadOS and development signing. Distinguish diagnostic prototypes from recovered gameplay.

- Keep `reference/Disco.app` immutable. Do not load its binaries during static inspection.
- Never commit the game, extracted assets, recovered game code, method dumps, device identifiers, signing material, or generated build products. Store generated data under `artifacts/`.
- Put Python inspection modules in `tools/disco_port/`, entry points in `tools/`, shared Swift input code in `runtime/InputCore/`, and the native app in `apps/ipad/`.
- Keep tooling dependency-free where practical. Validate binary offsets, counts, and version assumptions; fail explicitly on unsupported layouts.
- For binary and input logic, add tests that exercise malformed data, ownership/address resolution, viewport transforms, or interaction conflicts. Use `make test`.
- Use `make inspect` for the real reference integration check, and `make build-ipad` for an unsigned device build. Successful compilation does not establish on-device execution.
- Preserve Unity 2020.3.12f1 as the initial compatibility target. A recovered Unity project belongs under `artifacts/recovered-unity/` until a deliberate source selection policy is established.
- Record actual results and unresolved integration issues in repository documentation. Do not represent metadata signatures as recovered executable methods.

- The public build entry point is `make port`; keep it independent of scene recovery and decompilation. Run `make audit-release` before release commits. Never publish generated products or unreviewed logs.

- Android work targets the Galaxy Tab S10 Ultra initially. Keep its original host in `apps/android/` and `runtime/AndroidHost/`, with generated APKs, local signing, device reports and recovered shaders under `artifacts/android/`. Preserve the working iPad pipeline. Android probes must not be described as recovered gameplay.
- Keep supplied Windows installers under `reference/disco-win/` immutable too. Extract only into artifacts; never run the supplied installer or game binaries on the Mac. Windows and Mac metadata/native registrations are separate compatibility inputs.
