# Public source release

## Distribution boundary

Publish only this repository's original tooling, adapters, synthetic tests and documentation under MIT. Users must provide their own compatible game and separately licensed build tools.

Do not publish the game, extracted/recovered code or assets, generated C++/method dumps, patched Unity objects, derived frameworks, compiled apps/IPAs, asset manifests, screenshots, toolchain archives, device logs, identifiers, profiles or signing material. These belong under ignored `artifacts/` or `reference/`. The source audit rejects files outside an explicit allowlist and scans every reachable Git tree, not just the current checkout.

Offsets, hashes and small interface descriptions used by the original adapters document interoperability assumptions. The automated audit cannot prove authorship or decide whether a particular reverse-engineering/adaptation/distribution use is permitted.

## Rights review

MIT applies only to our original work. Game ownership does not itself establish permission to port or redistribute it; a locally built workflow is not automatic copyright clearance. Before claiming a legally cleared release, review the applicable game's license, Unity Editor/Runtime terms, supplied plugin terms and the relevant jurisdiction's interoperability rules with qualified advice as needed. No legal clearance has been obtained here.

Reference terms: [Unity legal](https://unity.com/legal), [Unity Editor terms](https://unity.com/legal/editor-terms-of-service/software), [Unity's terms history](https://github.com/Unity-Technologies/TermsOfService). Determine which versions apply to the selected editor/license. These links are review starting points, not a statement that current terms authorize this port. Terms were not refreshed during the offline release-preparation pass.

The repository bundles no third-party runtime or game artwork. Setup scripts obtain tools separately; their licenses remain with their owners. The game, Unity and plugin names identify required inputs and do not imply affiliation or endorsement. Keep bug reports limited to our code and redacted summaries; do not ask contributors to upload proprietary inputs.

## Local release checks

```sh
make test
make audit-release
make doctor
make port
```

The first two require no game. Public CI runs only those source checks; it receives no game, Unity license, developer credentials or device artifacts. Do not upload build logs as public CI artifacts.

Before publishing:

1. Review the final Git diff and `artifacts/release/audit.json`; resolve every finding. Rerun after committing so the final history is included.
2. Complete the applicable rights review. Do not describe the leak audit as legal approval.
3. Record actual fresh-build and physical-device results, including which changes remain device-untested. Back up saves before testing an updated app.
4. Export source with `git archive HEAD`, never zip the workspace. Inspect the archive listing and publish source only, with no generated attachments.

No GitHub repository, push, public upload or release was made during offline preparation. The audit is a heuristic safety check, not a guarantee against embedded third-party text or unknown secret formats. A human review remains required.
