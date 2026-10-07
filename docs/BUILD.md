# Local build

## Game input

Place your own macOS `Disco.app` at `reference/Disco.app`, or create a local symlink there to your copy. No command launches its executables on the Mac. Do not modify this reference.

The current adapters are specific to one inspected Unity 2020.3.12f1 ARM64 revision. `make doctor` validates four SHA-256 fingerprints in `tools/disco_port/build_inputs.py`: GameAssembly, IL2CPP metadata, Steam API and Amplify native plugin. The GameAssembly fingerprint is `0550f5a1e9fb9addba0b365908f21bc5a04a2f3979f1b2a640774a05a6c7ab52`. Storefront/version labels alone are insufficient. Other distributions or revisions need a separate compatibility audit; never bypass the fingerprint check to force one through.

Serialized-file layouts and object/resource hashes are checked during conversion. The full source bundle is fingerprinted before and after building. The reference must remain available for every full rebuild.

## Tool setup

1. Install/select Xcode 27.x and complete its first-run setup, including iOS build support. `xcodebuild -version` must select it.
2. Install Python 3.11+ and run `make setup-scenes`. The dependency lock is shared with optional inspection tools; the game build itself only uses UnityPy for bundle rewriting.
3. Run `make setup-unity`. It verifies the pinned official package sizes and SHA-256 hashes, extracts them under `artifacts/toolchains/`, and records the editor executable in `unity-editor-path.txt`. It runs no installer scripts.
4. Ensure you have Rosetta on Apple silicon and a valid license applicable to this editor. Open that editor manually if license activation is required. The workflow supplies no credentials or license bypass.
5. Run `make doctor`, then `make port`.

The archived editor/packages have reported invalid legacy signatures on the test Mac; why remains unresolved. The workflow does not disable system signature/security checks. If your Mac rejects the editor, resolve the installation with Unity's supported tooling. Do not assume the successful licensed installation on the test Mac makes first-time activation portable.

An existing exact-version installation with iOS Build Support can be used by writing its absolute `Unity.app/Contents/MacOS/Unity` path to `artifacts/toolchains/unity-editor-path.txt`. The export checks the Unity version; the BC adapter also checks the exact engine object hash.

`make port` does not install packages, access a device, sign or download. It requires installed dependencies and a working license. It always rebuilds the derived pipeline, so no stale checkpoint is treated as success. It replaces generated host/export content under `artifacts/`; keep independent experiments elsewhere.

## Outputs

| Path under `artifacts/` | Meaning |
| --- | --- |
| `recovered-unity/` | Empty original export host; original game data is selected later |
| `build/unity-ios/` | Pinned Unity iOS export |
| `build/native-engine-ios/` | Derived game project and private `Data/` tree |
| `build/native-engine-device-persistent/Build/Products/Debug-iphoneos/DiscoGeometryLab.app` | Unsigned app; historical product filename, not the geometry diagnostic |
| `reproducibility/<timestamp>/` | Step logs, build report and original-bundle fingerprints |
| `deployment-engine/` | Private signing, installation and device logs, created only by deployment |

`python3 tools/port.py plan` prints the complete command sequence. `make port` stops at the first failing step and reports its log. Fix the cause and rerun; generated content may be partially prepared after failure.

The data files live separately in `Documents/DiscoPortAssets/Data` on the iPad. The app only launches when the expected readiness manifest matches. Do not share the resulting app or data tree. For signing/deployment use [IPAD.md](IPAD.md).

## Reproduction scope

This is a repeatable source-input workflow, not a promise of byte-identical signed binaries. Xcode, timestamps, build paths, Unity caches and signing can change output bytes. Input fingerprints, dependency versions, exact Unity version, engine-object hash, object-body preservation and step success provide the reproducibility checks.

The offline clean-workspace test reuses the installed licensed editor and pinned Python environment; it does not establish that Unity activation or package acquisition works on a brand-new Mac. Device execution remains a separate test from compilation. See [STATUS.md](STATUS.md) for actual results.

## Troubleshooting

- **Unsupported game revision:** compare the reported digest to `build_inputs.py`; use the matching local game revision or add deliberately reviewed support for another one.
- **Editor exit/license error:** inspect `artifacts/build/unity-editor.log` and `unity-process.log`. Verify Rosetta, exact editor/iOS module and licensing manually.
- **No BC texture support:** this build stops before loading game textures on an unsupported GPU. No quality-reducing conversion or RGBA fallback is selected.
- **Missing/stale persistent assets:** rerun deployment, which verifies the generated data manifest before upload.
- **Signing unavailable:** refresh Xcode's authorized team, its Certificates/Identifiers/Profiles access and the required memory entitlements. Build success does not imply provisioning success.
- **Memory termination after visiting many scenes:** visited scenes still remain cached. Back up saves and capture a private diagnostic log; safe eviction is not implemented.

For diagnostic scans and automatic screenshots, rerun `tools/configure_engine_assets.py` with the normal options plus `--diagnostics`, then rebuild. Omit that flag on the next configuration to return to normal play. Never post unreviewed device logs or crash reports publicly.
