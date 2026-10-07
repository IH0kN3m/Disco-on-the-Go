# iPad compatibility

| Area | Supported/verified boundary |
| --- | --- |
| Verified device | 13-inch M4 iPad Pro, 16 GB, stock iPadOS 27.0; previous gameplay build |
| Other iPads | Physical models accepted for development deployment; not yet device-verified |
| GPU | Native `MTLDevice.supportsBCTextureCompression` is required; checked before game initialization |
| Memory | Opening room approximately 4.0 GiB; tested subsequent scenes approximately 5.1 GiB. The tested 16 GB iPad still provides roughly a 6 GiB process budget |
| OS/toolchain | Deployment target iPadOS 17+, actual device testing only on 27.0; build tools Xcode 27.x |
| Display | Single full-screen landscape window; aspect 1.25–1.6, dimensions up to 16,384 pixels; tests include 13-inch, 11-inch/Air and mini-shaped viewports |
| Input | Direct touch, pinch zoom and native virtual controller verified on M4 |

Model acceptance is not a claim that every iPad can run the game. Native BC capability is queried from Metal, not guessed from the model string. A GPU without it currently stops with an explicit unsupported-GPU log before the expensive texture fallback. M1/M2 and other devices without native BC are not made compatible merely by removing the model whitelist. A texture conversion or bounded decode implementation would be separate work and needs visual-quality evaluation.

The display adapter uses actual viewport dimensions and retains the existing 2048-unit UI reference height. Wider tablet ratios override the game's fixed 4:3 fitter and resize the reference canvas proportionally. These changes have synthetic policy tests and must still be checked on each physical form factor. Portrait, external widescreen, split view and Stage Manager resizing are not supported; one fixed landscape direction is used.

More physical RAM does not guarantee a larger app memory allowance. Development signing requests increased memory and extended virtual addressing; iPadOS controls the actual allowance. No memory policy or image-quality downgrade is silently selected for smaller devices. Long sessions can exceed the allowance because visited scenes remain cached.

Normal-play builds omit periodic VM-region scans, five-second main-thread allocation/scene inventories, startup BC readback experiments and automatic PNG captures. Lightweight 30-second process-memory sampling, startup checks and memory-warning evidence remain. This removes diagnostic work, but no frame-rate or battery-life improvement has been measured yet. Original texture blocks, mip levels, resolution, UI scale and frame-rate policy are preserved.
