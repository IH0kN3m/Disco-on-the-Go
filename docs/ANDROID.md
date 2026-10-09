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

The supplied Windows GOG installer (`winkay16062026_memfix`, 91668) has now been inspected. Selected files were extracted with innoextract 1.9 without running the installer; all four installer/part hashes were unchanged afterward. The installer inventory contains no managed game assembly set. All 24 extracted executable/plugin files are native PE, including x64 `GameAssembly.dll` and `UnityPlayer.dll`; this is another IL2CPP build, not a C# rebuild shortcut.

Its serialized data identifies Unity 2020.3.12f1. The four inspected root containers contain 78 shaders with platform IDs 4/15 (Direct3D 11/OpenGL Core), with no Android variants. All 78 match a Mac shader by container/name and have identical compressed OpenGL segment payloads. This comparison does not cover every addressable bundle or establish material/render equivalence.

Windows metadata v27 contains 16,187 types and 112,430 method records versus Mac's 14,861/102,219. There are 102,083 shared method labels when matching assembly, qualified name and parameter count; this is not a code-equivalence check. Windows includes additional desktop frameworks, and even Assembly-CSharp type counts differ (2,814 versus 2,812). Do not mix metadata, native registrations or offsets between the builds.

**Decision:** retain the Mac ARM64 runtime and matching data as the native Android baseline. The inspected Windows build offers neither managed game IL nor new OpenGL shader payloads, and reusing its native code adds x64 translation. Keep Windows as a separate comparison input. The next runtime gate is an Android-compatible replacement for the Mac loader/runtime ABI, not another asset conversion.

## Remaining engineering gates

1. **Runtime:** original ARM64 IL2CPP startup, metadata invocation and one full garbage collection now pass on the target tablet. Complete C++ exception/unwind compatibility, remaining services, sustained collector tests and Unity Android integration are still required. Startup success does not cover arbitrary game execution.
2. **Shaders:** the first 79 sampled objects contain Metal and OpenGL Core platform IDs, not GLES/Vulkan. Readable GLCore source is available. The current conversion experiment preserves arithmetic but changes the shader-language profile, precision defaults and desktop uniform-location declarations. Unity bindings, keyword variants, render state and visual correctness remain to be rebuilt/verified; unsupported features must fail explicitly.
3. **Textures:** the iPad's native BC path cannot run on this GPU. The BC1/BC3 GPU block experiment above is the first step toward decoded textures with bounded residency. The other formats and Unity integration remain unresolved. BC→ASTC encoding introduces another lossy compression step; it is not a zero-loss substitute and is not selected automatically.
4. **Game integration:** original data paths, Amplify CPU codecs, streaming, Android lifecycle, touch/controller input, saves and full scene transitions. The existing iPad work supplies evidence and original adapters, not a ready Android binary.
5. **Packaging:** the current APK is small; full-game packaging/data installation is not implemented. Do not promise that all desktop assets fit inside one APK or that a successful Android compile is gameplay.

## Mapped ARM64 runtime checkpoint

Verified on the physical SM-X920 on 10 October 2026:

- Four original image segments mapped across 49,086,464 virtual bytes, with zero-filled BSS and original segment protections. Staging is writable, then executable segments become RX; no RWX mapping is used.
- All 320,805 classic-dyld pointer rebases applied. Static locations/targets independently match Apple's `dyld_info -fixups` output exactly, including two tagged RTTI pointers. The mapper verifies original pointer values and executable-byte equality.
- Parsed 243 exports, 364 binding slots and 10 initializers. Bind records include five weak replacements; identical duplicate bind operations are collapsed. Unsupported layouts fail explicitly.
- All ten original initializers complete. `il2cpp_init` reads the supplied matching metadata and returns success. Domain/assembly/class/method lookup finds `UnityEngine.Vector3.Dot`; original `il2cpp_runtime_invoke` returns a boxed float that unboxes to 32. This exercises the metadata/object runtime, beyond calling a pinned arithmetic address.
- Original `il2cpp_gc_collect(2)` returns. A separate synthetic thread check performs 16 suspend/register-capture/resume cycles, rejects undersized output and token release while suspended, and checks that the worker stops making progress while parked. This is not a sustained multithreaded GC or game-lifecycle test.
- 157 distinct import symbols resolve through explicit adapters (166 binding records). **177 remain unsupported**, including exception/unwind, portions of libc++ and Apple services. Unsupported function calls abort with their symbol/caller offset; unresolved data symbols point into inaccessible guard pages. They never masquerade as successful operations or readable C++ objects.
- Original allocator and timebase checks still pass. Executable bytes remain unchanged; adapters live in the original Android host.

The offline startup traversal finds 887 direct-reachable functions, 119 imports and 203 indirect sites. It is an audit aid, not complete coverage. `make inspect-android-initializers` regenerates both initializer and boot reports without executing supplied binaries on the Mac.

The bridge owns native mutex/condition/RW-lock objects in address-keyed tables rather than overwriting Darwin storage. It handles Darwin TLS keys, semaphores, static guards, thread attributes, selected file/stat/mapping/locale/system queries, stack-based variadic arguments and Apple's 24-byte alternate string layout. ARM64 constructors/destructors must return the original object pointer: omitting that return corrupted a vector during array-metadata setup; a regression test now checks this contract.

The collector bridge suspends only registered threads in this process through a reserved signal and futex handshake. Token release waits for a completed resume. The `_setjmp` adapter only spills registers for the pinned collector callsite; staging rejects changed callsites or a longjmp import. It does not implement general nonlocal jumps. Cancellation state is bookkeeping only: this source imports no cancellation request API. Darwin/Bionic error-code coverage is incomplete.

The mapped image, metadata and registered callbacks are retained for the diagnostic process lifetime. Shutdown/finalization, exception propagation through mapped frames, additional library roots, repeated host initialization and Android lifecycle integration remain unverified. Do not use this diagnostic as a general-purpose Mach-O loader.

```sh
make inspect-android-initializers
make build-android-runtime-probe
make deploy-android-runtime-probe
```

The build stages the hash-checked image and binary load plan into `artifacts/android/runtime/`, packages them into `artifacts/android/build-mapped-runtime/disco-android-probe.apk`, and runs them only on the selected Android device. This APK contains supplied game code and stays private. CPU-side malformed-input tests map synthetic non-executable fixtures only; supplied binaries are never loaded on the Mac.

Source layout: `tools/disco_port/dyld_plan.py` validates classic dyld streams; `tools/disco_port/arm64_calls.py` audits direct initializer dependencies; `runtime/AndroidHost/MappedImage.h` owns mapping and relocation; `DarwinBridge`, `DarwinString`, `DarwinSystem`, `DarwinVarargs`, `DarwinThreads` and `DarwinABI.S` implement original, limited ABI adapters; `RuntimeProbe.cpp` drives the startup and device checks. The shared regression suite passes 89 Python and 4 Swift tests. `make inspect` and the source/history leak audit pass. Synthetic host tests cover opaque-storage guards, held-lock destruction, timeouts, TLS isolation, string ownership/constructor returns, sysctl buffer bounds and malformed variadic formats. Supplied native binaries are never executed on the Mac.

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

For the supplied GOG Windows build, install `innoextract` (tested Homebrew 1.9), then:

```sh
python3 tools/extract_windows_probe.py reference/disco-win
python3 tools/inspect_windows_input.py artifacts/android/windows-extracted
.venv/bin/python tools/compare_windows_input.py
```

The extractor selects only inspection files, records source hashes before/after, and refuses to overwrite an extraction belonging to different inputs. Keep the setup EXE and all BIN parts together. `--include` paths are literal paths/directories, not shell globs. An already extracted game can be passed directly to `inspect_windows_input.py`; its PE/CLI reader checks owned IL body ranges and counts trivial/placeholder-like bodies separately. None of these tools loads a supplied executable. Comparison outputs and installer inventories stay under `artifacts/android/`.

Enable USB debugging and authorize the Mac. Initial discovery accepts one authorized physical ARM64 Tab S10 Ultra. To select another intended tablet or disambiguate multiple devices, create `artifacts/local-android.json` with a `device_identifier` field. Device selection and actual CPU/OS checks precede installation; compatibility is established by the runtime report, not model-name acceptance.

Outputs:

- `artifacts/android/build-capabilities/disco-android-probe.apk`: original capability diagnostic.
- `artifacts/android/build-original-leaf/disco-android-probe.apk`: local original-leaf test, optionally including private shader samples.
- `artifacts/android/device/capabilities.json`: measured report, retrieved via `run-as` from the debuggable app.
- `artifacts/android/signing/`: local development keystore; retain it for updates and never commit it.

Packages containing the original leaf or recovered shaders are private derived game products and must not be published. Generated shaders, code bytes, import lists, device identities and signing material stay under ignored artifacts. The reference app remains immutable and is never loaded as native code on the Mac.

References: [Android ABIs](https://developer.android.com/ndk/guides/abis), [Apple ARM64 conventions](https://developer.apple.com/documentation/xcode/writing-arm64-code-for-apple-platforms), [Android 16 KiB pages](https://developer.android.com/guide/practices/page-sizes), [Unity 2020 shader platform enum](https://github.com/Unity-Technologies/UnityCsReference/blob/2020.3/Editor/Mono/Graphics/ShaderCompilerData.cs).
