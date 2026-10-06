# Inspection tooling

`make inspect` reads metadata and both GameAssembly architecture slices. It writes `artifacts/inspection/methods.sqlite` and a source-hash summary. No inspected game code is executed.

```sh
python3 tools/methods.py SaveGame --image Assembly-CSharp.dll --arch arm64
python3 tools/methods.py GetMouse --arch x86_64 --json
make audit
make setup-scenes
make scenes
.venv/bin/python tools/inspect_scenes.py --scene 6
make recover-scene
```

The metadata reader targets the v27 table layout in Unity 2020.3.12f1. It validates table bounds, record strides, type ownership, method tokens, and field/parameter ranges. Type indexes are raw; nested declaring-type resolution, generic instantiations, field offsets, and method bodies remain unresolved.

The native mapper identifies CodeGenModule prefixes by assembly name, maximum method token, and executable pointer validation. It supports the actual `il2cpp` code section. Addresses are unslid virtual addresses. `slice_offset` is relative to the thin architecture slice; `file_offset` is relative to the original universal binary. A zero pointer is recorded as `no_direct_pointer`, without inferring a method's behavior.

Scene inspection uses pinned UnityPy dependencies. It indexes built scenes and exports built-in components for the selected scene under `artifacts/scenes/`. Object references retain Unity file IDs and path IDs. Referenced asset payloads and custom MonoBehaviour data are not exported. Parsing errors are recorded and produce a failing exit status.

Scene recovery uses UnityPy 1.25.4 and TypeTreeGeneratorAPI 0.0.10. It statically parses the ARM64 binary buffer to generate serialization layouts. AssetsTools is the primary backend; AssetStudio handles layouts that fail complete reads. A compatibility adapter fixes assembly naming and MonoBehaviour enabled-byte alignment. Every decoded script must consume its complete payload and match the canonical Unity header. This recovers serialized values, not method implementations.

`artifacts/recovery/scene-06/recovery.json` is the current manifest. It records source hashes, selected backends, exports, and errors. Only files referenced by that manifest/components belong to the current run; unused files from earlier runs may remain. The command exits unsuccessfully on unresolved errors. Non-finite serialized floats use explicit `{"$float":"Infinity"}` / `-Infinity` / `NaN` markers.

Reference resolution uses the owning file's one-based external table and validates object IDs and paths. Resource reads validate offset/size, with a 256 MiB span limit. Mesh indices must belong to the vertex buffer; positions must be finite. Exported mesh JSON preserves Unity local coordinates. Texture PNGs are diagnostic decodes with vertical flipping, not iOS-ready GPU texture packages.

Current scope: selected built-in components, all custom script values, directly referenced meshes/materials, and standard material Texture2D slots. Unity built-in resources are marked as runtime dependencies. Colliders, animation, audio, navigation, executable scripts, shaders, Addressables traversal, and Amplify virtual texture pages still require integration.

Format references: [IL2CPP metadata structures](https://github.com/Perfare/Il2CppDumper/blob/master/Il2CppDumper/Il2Cpp/MetadataClass.cs), [native registration structures](https://github.com/Perfare/Il2CppDumper/blob/master/Il2CppDumper/Il2Cpp/Il2CppClass.cs), [UnityPy](https://github.com/K0lb3/UnityPy), [TypeTreeGeneratorAPI](https://github.com/UnityPy-Org/TypeTreeGeneratorAPI). The repository contains original adapters/readers; recovery dependencies are installed locally.
