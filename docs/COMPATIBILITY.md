# Compatibility and limits

Only the exact Mac game revision checked by `make doctor` is supported. See [input requirements](BUILD.md#game-input).

| Platform | Device-tested baseline | Requirements and limits |
| --- | --- | --- |
| iPad | 13-inch iPad Pro M4, 16 GB, stock iPadOS 27 | iPadOS 17+, native Metal BC textures, sufficient process headroom, development signing with memory capabilities |
| Android tablet | Galaxy Tab S10 Ultra, Mali-G720, about 11.26 GiB reported RAM | ARM64, API 28+, GLES 3.2; unsupported BC textures decode at runtime |
| Android handheld | Retroid Pocket 5, Adreno 650, about 7.52 GiB reported RAM | Opening gameplay and quick-save tested; later areas need testing |

Other iPads and Android devices are untested. The runtime checks required capabilities; passing those checks is not proof of a complete playthrough.

The 16 GB M4 has shown roughly a 6 GiB process limit even with requested memory entitlements. Lazy scene loading avoids eagerly retaining the entire world, but visited areas remain cached. Long sessions and larger sequences of area transitions may still exceed available memory. Safe scene eviction is not implemented.

Opening dialogue, textured gameplay, touch movement, saving and transitions work on the M4. Samsung menus, dialogue, room/outdoor rendering and highlighting are verified. Retroid opening gameplay and quick-save are verified. Background/resume, every controller action, every shader variant on each driver and the full game remain unverified.

The build preserves source texture dimensions/data. Android changes shader/platform payloads and unsupported render-target formats. Audits verify their documented scope; they do not prove lossless rendering across the game.

Development signing is for local installation. Keep your identifiers/keys stable, back up saves before updates, and renew iPad provisioning before its expiry.
