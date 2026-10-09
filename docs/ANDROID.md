# Android port work

Target: Samsung Galaxy Tab S10 Ultra first, with capability-based support for other ARM64 tablets. The iPad pipeline remains separate and working. **The current APK is a diagnostic, not the playable game.**

## Verified on the tablet

9 October 2026, physical SM-X920:

- ARM64-only Android API 36, 4 KiB process pages, 2960×1848 display.
- Reported physical memory: 12,085,673,984 bytes (approximately 11.26 GiB). Java's 256 MiB heap class is not a native process memory limit.
- Mali-G720-Immortalis MC12: Vulkan initialization succeeds; BC1/3/6H/7 sampling is unsupported. ASTC LDR and ETC2 are supported; ASTC 4×4 reports sampling/filter support.
- The pinned original 24-byte ARM64 `Vector3.Dot` leaf was linked unchanged into an Android ELF library. Three arithmetic cases passed, including `Dot((1,2,3),(4,5,6)) = 32`. No original runtime initialization, object system, exception handling or game logic is implied.
- An initial 24 shader variants from one shader compiled and linked under GLES. A broader sample has 13 unique pairs across 13 shader objects: 12 link under GLES 3.2 after precision/profile adaptation. The remaining VR-layer sample requires the unsupported `GL_AMD_vertex_shader_layer` extension; it is not silently removed. One oversized shader blob was rejected by the extraction bound. Detailed results are local in `artifacts/android/device/capabilities.json` and `artifacts/android/shaders/report.json`. Shader compilation is not rendered-fidelity verification.
- Original GLES compute decoding of BC1 RGBA and BC3 passed 2,048 synthetic pixels against the CPU reference, with zero mismatches and no GL error. Each dispatch uses a 4 KiB output buffer. This test also runs in the content-free APK. It establishes block decoding only: BC6H/BC7, texture uploads, residency, filtering, sRGB behavior and rendered fidelity remain pending. No ASTC recompression is used.

Decoder regression tests cover known RGB/alpha values, both endpoint orders, packed selectors crossing word boundaries, rejected buffers and output guards. A development comparison with `texture2ddecoder 1.0.6` matched 358,720 channels within shared semantics across 8,192 random blocks. That library is not an oracle for BC1 RGBA alpha or reversed-endpoint BC3 RGB; those excluded cases have explicit tests following the [Khronos S3TC specification](https://registry.khronos.org/OpenGL/extensions/EXT/EXT_texture_compression_s3tc.txt). Native GPU rounding and complete image fidelity are not established by these tests.

## Source choice

The macOS ARM64 build avoids instruction-set translation and supplies known metadata/assets. It is the current native-port research baseline. Android requires ELF, Bionic/POSIX APIs and Android ABI conventions; changing a Mach-O platform tag, as in the iPad experiment, cannot make it load.

Static inspection found 334 imports: 34 Darwin/Objective-C services, 91 C++ ABI/exception imports, 32 thread APIs, 156 names also found in Android's C libraries, and 21 without a name match in the selected API-28 C libraries. Names that match still need signature, structure, flags and error-code review. No `svc` instruction matches were found in the inspected executable sections. This does not prove portability or that every dependency has been identified.

Windows x64 introduces CPU translation if its native binary is reused. However, a Windows build containing real managed assemblies rather than IL2CPP, or useful shader variants, could substantially simplify rebuilding. The Windows input has not yet been supplied/inspected; do not assume its scripting backend or version. It is being downloaded.

## Remaining engineering gates

1. **Runtime:** choose between managed-code rebuilding if suitable inputs exist, or an ARM64 Mach-O/ELF compatibility implementation. The latter needs rebasing/binding, C++ runtime and unwind compatibility, Darwin thread/structure wrappers, Apple service replacements and Unity Android integration. The arithmetic test proves only a tiny shared calling-convention case.
2. **Shaders:** the first 79 sampled objects contain Metal and OpenGL Core platform IDs, not GLES/Vulkan. Readable GLCore source is available. The current conversion experiment preserves arithmetic but changes the shader-language profile, precision defaults and desktop uniform-location declarations. Unity bindings, keyword variants, render state and visual correctness remain to be rebuilt/verified; unsupported features must fail explicitly.
3. **Textures:** the iPad's native BC path cannot run on this GPU. The BC1/BC3 GPU block experiment above is the first step toward decoded textures with bounded residency. The other formats and Unity integration remain unresolved. BC→ASTC encoding introduces another lossy compression step; it is not a zero-loss substitute and is not selected automatically.
4. **Game integration:** original data paths, Amplify CPU codecs, streaming, Android lifecycle, touch/controller input, saves and full scene transitions. The existing iPad work supplies evidence and original adapters, not a ready Android binary.
5. **Packaging:** the current APK is small; full-game packaging/data installation is not implemented. Do not promise that all desktop assets fit inside one APK or that a successful Android compile is gameplay.

## Reproduce the diagnostic

Installed prerequisites: macOS, JDK 17, Android SDK platform 36, build-tools 36.0.0, NDK 27.2.12479018 and platform-tools/ADB. The build uses SDK tools directly and needs no Gradle/Maven download. `--sdk` and `--java-home` override local discovery. Native libraries and the APK are aligned for 16 KiB pages, although the tested tablet currently uses 4 KiB.

```sh
make build-android-probe           # Original capability host, no supplied game content
make deploy-android-probe          # Includes the synthetic BC1/BC3 compute test
make build-android-cpu-probe       # Adds the local, hash-checked original arithmetic leaf
make inspect-android-runtime      # Static import/dependency report, no native execution on Mac
make inspect-android-shaders      # Bounded local shader sample extraction
python3 tools/build_android.py --with-original-kernel --with-shader-samples
make deploy-android-cpu-probe      # Installs that local CPU-probe APK and retrieves its report
```

The exact Unity 2020.3.12f1 Android module has also been downloaded, hash-verified and installed alongside the local iOS module. Reproduce with `python3 tools/setup_unity_android.py`; it extracts the official package without executing installer scripts. This does not yet establish a working Unity Android export or game runtime.

`python3 tools/inspect_windows_input.py /path/to/windows-game` is prepared for the incoming Windows input. It distinguishes native PE files from CLI metadata and checks owned IL body ranges; trivial/placeholder-like bodies are counted separately. It never loads a supplied executable.

Enable USB debugging and authorize the Mac. Initial discovery accepts one authorized physical ARM64 Tab S10 Ultra. To select another intended tablet or disambiguate multiple devices, create `artifacts/local-android.json` with a `device_identifier` field. Device selection and actual CPU/OS checks precede installation; compatibility is established by the runtime report, not model-name acceptance.

Outputs:

- `artifacts/android/build-capabilities/disco-android-probe.apk`: original capability diagnostic.
- `artifacts/android/build-original-leaf/disco-android-probe.apk`: local original-leaf test, optionally including private shader samples.
- `artifacts/android/device/capabilities.json`: measured report, retrieved via `run-as` from the debuggable app.
- `artifacts/android/signing/`: local development keystore; retain it for updates and never commit it.

Packages containing the original leaf or recovered shaders are private derived game products and must not be published. Generated shaders, code bytes, import lists, device identities and signing material stay under ignored artifacts. The reference app remains immutable and is never loaded as native code on the Mac.

References: [Android ABIs](https://developer.android.com/ndk/guides/abis), [Apple ARM64 conventions](https://developer.apple.com/documentation/xcode/writing-arm64-code-for-apple-platforms), [Android 16 KiB pages](https://developer.android.com/guide/practices/page-sizes), [Unity 2020 shader platform enum](https://github.com/Unity-Technologies/UnityCsReference/blob/2020.3/Editor/Mono/Graphics/ShaderCompilerData.cs).
