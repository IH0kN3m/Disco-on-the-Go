# Implementation status

7 October 2026

## Offline release preparation — 7 October 2026

- Normal play disables repeated VM scans, main-thread allocator/scene inventories, BC readback experiments and automatic screenshots. Full texture quality, UI scale and frame-rate policy are unchanged. Performance gains have not been measured on device.
- `make doctor` validates the exact game revision and tools; `make port` runs the complete unsigned pipeline with per-step logs, exclusive workspace ownership and source immutability checks. An empty original Unity export host removes scene recovery/decompilation from the build prerequisites.
- Fresh-directory reproduction passed all 12 steps using only public source plus the supplied game, installed licensed Unity editor and pinned Python environment. All 2,203 source-bundle entries were unchanged. The new project registers 8,163 bindings and 62 modules and retains all 76 root serialized files. Fresh tool download/license activation was not retested offline.
- 70 Python tests and 4 Swift tests pass. The unsigned UIKit harness build passes. Source/leak checks found no findings in the working tree or the six existing Git commits. The release procedure reruns the audit after the final commit.
- The main workspace also completed the full unsigned pipeline, with the same derived asset manifest as the fresh-directory build. The supplied reference remained unchanged in both runs.
- Deployment can select a team-owned app identifier and verifies app/container ownership; existing installs retain their identifier by default.
- Deployment accepts physical iPads on iPadOS 17+; full-screen tablet viewport policy covers 1.25–1.6 aspect ratios. Native BC is required at runtime. Other models, lower memory budgets and these display changes are not device-verified.
- Updated README/build/device/compatibility/release instructions and source-only CI are prepared. No iPad installation, GitHub upload or publication was performed. Applicable game, Unity and plugin rights still need review; no legal clearance is claimed.

## Prepared build installed — 7 October 2026

The prepared build was development-signed, installed over the existing M4 app and launched with the same bundle identifier. The rebuilt asset manifest required a refresh. All six save files and the settings file were backed up locally; no app deletion or container reset was performed.

The device log confirms Apple M4 native BC support, completed Unity application loading, the full 2752×2064 landscape profile and approximately 2.46 GiB startup footprint at the 30-second sample. Periodic diagnostic scans/readbacks/captures are disabled. Save loading, input and a transition on this new build still await user confirmation; a full playthrough remains unverified.

Deployment initially rejected CoreDevice's structured OS-version object. The parser now reads its `stringValue`, with regression coverage for valid and malformed objects. Real device validation and deployment subsequently passed. The current suite passes 71 Python tests and 4 Swift tests.

## Prior device evidence

| Work | Result |
| --- | --- |
| Static metadata index | 92 images, 14,861 types, 102,219 methods, 60,329 fields |
| Native addresses | 96,723 mapped methods per architecture; 89 modules in ARM64 and x86_64 |
| Unmapped direct pointers | 5,496 methods per architecture; generics and abstract methods need further analysis |
| Scene inventory | 36 built scenes indexed |
| Initial recovery target | Whirling floor 2, build index 6; 1,617 objects, 998 built-in components exported |
| Custom scene data | All 414 MonoBehaviour components decoded across 58 classes; 375 via AssetsTools, 39 via AssetStudio |
| Asset recovery | 67 meshes (18,327 vertices, 19,395 triangles), 58 materials, 57 standard textures exported locally |
| References | 3,846 component references inspected; 16 Unity built-in runtime dependencies marked; zero unresolved errors within the documented scope |
| iPad host | UIKit touch harness verified; separate Unity geometry diagnostic installed on the M4 |
| Verification | 62 Python tests and 4 Swift tests pass; real-reference inspection, texture census, VTC sample recovery, UIKit unsigned build, Unity export and ARM64 engine build succeed |
| Physical M4 | Paid development signing, installation and launch over local network succeeded on a real 13-inch M4, iPadOS 27.0; user confirmed harness checks work |
| Amplify textures | 40 VTC2 containers and 311,680 page records validated; 640 Unity Crunch plane samples decoded; original derived ARM64 CPU codec plugin loads on M4 and removes missing-plugin exceptions; desktop OpenGL calls explicitly guarded; full room fidelity pending |
| Unity toolchain | Exact 2020.3.12f1 editor/iOS module unpacked locally; existing license works; Xcode 27 export/compile/sign/install succeeds |
| Unity scene diagnostic | 373 nodes and 67 meshes staged; UIKit lifecycle, shader stripping, and saved inactive groups handled; 82 active mesh instances; post-splash frame retrieved from the real M4 confirms rendering; sampled native transform matches source; original visual fidelity remains pending after user distortion reports |
| Native ARM64 runtime | Derived module loaded on stock M4; original runtime/metadata initialized; original Vector3.Dot invocation returned 32; executable section hashes unchanged |
| Original runtime + iOS engine | Single original provider linked; 8,163 bindings registered; Metal/startup succeeded on M4; original Time methods reached live engine state, with frames advancing 0 → 61 |
| Original startup data | Complete 9.6 GB app installed; original localization/settings/game-data, intro and area code executed; 76 root files, 50 startup and 1,827 addressable containers retagged; object/resource bodies unchanged; dialogue bundle loaded; original copyright/loading UI and main menu captured; virtual-texture path errors fixed; loading memory and rendering issues remain |
| Original Steam library | Derived ARM64 library loaded; client initialization failed without a Steam client; game continued with achievement provider NONE |
| Device iteration | Persistent 9.6 GB asset tree seeded and checked by manifest; app reduced to about 96 MB; repeat deployments skip matching data uploads; actual launch settings validated |
| Memory diagnosis | Physical RAM confirmed; roughly 6 GiB process headroom observed with requested capabilities; full-resolution warning at 4.81 GiB footprint with 2.72 GiB graphics-driver allocation; debugger confirms EXC_RESOURCE at 6,144 MB on New Game → Thinker → Continue; menu survives at about 4.94 GiB; retained allocations still under investigation |
| BC hardware | Native Metal accepts BC1/3/7/6H; synthetic BC1 GPU readback passes; derived pinned-engine BC bridge enables all four and eliminates game fallback warnings; real-asset fidelity pending |
| Texture streaming census | 5,190 nonempty Texture2D objects across 1,952 files; one mip-streaming flag; 3,787 BC objects estimate 1.59 GiB compressed versus 8.29 GiB fallback across all inspected containers, not runtime residency |
| Scene residency | Original menu retains 33 loaded scenes. Validated runtime coroutine adapters reduce this to Church + Lobby (2), then demand-load Whirling floor 2 (3). Menu footprint about 2.5 GiB; visited scenes remain cached; eviction and cancellation cleanup pending |
| Original gameplay | User confirms opening dialogue, textured room rendering, tap movement, saving and area transitions. GPU frames show the original room and outdoor scene. Initial room holds about 4.0 GiB; subsequent retained areas reach about 5.1 GiB. Full fidelity and long-session stability remain unverified |
| Tablet display | Landscape backbuffer 2752×2064; original camera/UI profile adapted to 4:3. User confirms full-screen world, aligned bottom bar and correct appearance. Fixed landscape orientation; reverse-landscape rotation remains pending |
| Additional touch controls | User confirms controller movement, A/B interaction, hiding the pad and pinch zoom work. Small icon toggles dual sticks, D-pad, ABXY, shoulders and triggers; Menu uses Escape. Device confirms one Unity joystick and original InControl selecting Apple MFi Controller. UI scale is unchanged |
| Memory policy | Live signed entitlements confirmed. Removing the debugging entitlement still leaves roughly 6 GiB headroom before Unity starts. Read-only kernel-limit query denied; reason for device policy remains unresolved |
| Simulator | Harness previously launched and layout inspected on the installed 13-inch M5 simulator |

Next: preserve state across bounded scene eviction, test save/reload and longer play across more areas, and compare full visual fidelity. A complete playthrough is not established.
