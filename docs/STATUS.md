# Implementation status

7 October 2026

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
| Verification | 37 Python tests and 4 Swift tests pass; real-reference inspection, VTC sample recovery, UIKit unsigned build, Unity export and ARM64 build succeed |
| Physical M4 | Paid development signing, installation and launch over local network succeeded on a real 13-inch M4, iPadOS 27.0; user confirmed harness checks work |
| Amplify textures | 40 VTC2 containers and 311,680 page records validated; 640 Unity Crunch plane samples decoded; placement and plane 1 pending |
| Unity toolchain | Exact 2020.3.12f1 editor/iOS module unpacked locally; existing license works; Xcode 27 export/compile/sign/install succeeds |
| Unity scene diagnostic | 373 nodes and 67 meshes staged; UIKit lifecycle, shader stripping, and saved inactive groups handled; 82 active mesh instances; post-splash frame retrieved from the real M4 confirms rendering; sampled native transform matches source; original visual fidelity remains pending after user distortion reports |
| Native ARM64 runtime | Derived module loaded on stock M4; original runtime/metadata initialized; original Vector3.Dot invocation returned 32; executable section hashes unchanged |
| Original runtime + iOS engine | Single original provider linked; 8,163 bindings registered; Metal/startup succeeded on M4; original Time methods reached live engine state, with frames advancing 0 → 61 |
| Original startup data | Complete 9.6 GB app installed; original localization/settings/game-data, intro and area code executed; 76 root files, 50 startup and 1,827 addressable containers retagged; object/resource bodies unchanged; dialogue bundle loaded; original copyright/loading UI captured; virtual-texture path errors fixed; loading memory and rendering issues remain |
| Original Steam library | Derived ARM64 library loaded; client initialization failed without a Steam client; game continued with achievement provider NONE |
| Simulator | Harness previously launched and layout inspected on the installed 13-inch M5 simulator |

Next: resolve loading memory use and native texture/GPU support, reach the main menu, then integrate touch gameplay. Original startup code runs on the M4; playable gameplay is not verified.
