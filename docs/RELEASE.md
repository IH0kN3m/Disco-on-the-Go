# Public source release

Publish this repository's original tooling, adapters, synthetic tests and documentation. MIT applies only to that work. Users provide their own game and separately licensed tools; game ownership and local building do not establish permission for every adaptation or distribution use. Applicable game, Unity and plugin rights still require review. No legal clearance is claimed.

Do not publish game inputs, extracted assets/code, derived icons, method dumps, shaders, generated libraries/apps/APKs/IPAs/OBBs, signing material, device identifiers, screenshots or unreviewed logs. `reference/` and `artifacts/` are ignored. The release audit checks an allowlist and all reachable Git history; it is a heuristic leak check, not a legal or authorship decision.

Before a source release:

```sh
make test
make audit-release
make doctor
make port
make doctor PLATFORM=android
make port PLATFORM=android
```

Review the final diff and `artifacts/release/audit.json`. Resolve findings. Rerun the audit after the final commit so history is included. Record actual build and device results in [STATUS.md](STATUS.md).

Export source with `git archive HEAD`, never by zipping the workspace. Inspect the archive listing. Attach no generated game products, private logs or icons. Public CI runs source checks without a game, Unity license, credentials or device.

No repository push, public upload or release is implied by local preparation. Existing development history remains local until deliberately published; the audit must pass on every reachable tree.
