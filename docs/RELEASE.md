# Source release checks

Publish only original tooling, adapters, synthetic tests and documentation. Keep game data, derived code/artwork, builds, signing material, device identifiers and private logs out of Git.

Before releasing:

```sh
make test
make audit-release
make doctor && make port
make doctor PLATFORM=android && make port PLATFORM=android
```

Review the diff and `artifacts/release/audit.json`; resolve findings and rerun the audit after committing. Update [device results](STATUS.md). Export with `git archive HEAD`, not a workspace ZIP.

The audit checks leaks; it does not establish legal clearance.
