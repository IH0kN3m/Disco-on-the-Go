# Project conventions

Disco on the Go builds the complete game locally from the user's macOS app. Preserve the verified iPad Pro M4 and Galaxy Tab S10 Ultra baselines. Distinguish tested devices from untested models; gate compatibility by actual GPU/memory capabilities.

- Keep `reference/Disco.app` and any `reference/disco-win/` inputs immutable. Never execute supplied binaries/installers on the Mac.
- Never commit the game, extracted assets/code, derived icons, method dumps, device identifiers, signing material or generated products. All generated material belongs under `artifacts/`.
- Put Python modules in `tools/disco_port/`, entry points in `tools/`, iPad host code in `apps/ipad/`, shared Unity adapters in `runtime/UnityHost/`, and Android host code in `apps/android/` and `runtime/AndroidHost/`.
- Keep tooling dependency-free where practical. Validate binary offsets, counts, layouts and ownership; fail explicitly on unsupported inputs.
- Keep tests for production binary/input logic, malformed data, ownership, viewport transforms and interaction conflicts. Use `make test`; do not restore obsolete diagnostic harnesses.
- Keep Unity 2020.3.12f1 as the compatibility target. `make port` must remain independent of decompilation and scene recovery. Builds remain offline after explicit setup/license activation.
- Use `make inspect` for real-reference integration and `make build-ipad`/`make build-android` for staged code-only rebuilds. Compilation or launch submission does not establish device gameplay.
- Keep existing app identifiers, local signing keys and save containers stable during updates. Branding must not publish supplied artwork.
- Record actual results and unresolved limits in documentation. Do not claim a complete playthrough, universal fidelity or legal clearance from static audits.
- Run `make audit-release` before release commits and again afterward. Never publish generated products or unreviewed logs.
