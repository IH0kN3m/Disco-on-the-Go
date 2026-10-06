# Inspection tooling

`make inspect` reads metadata and both GameAssembly architecture slices. It writes `artifacts/inspection/methods.sqlite` and a source-hash summary. No inspected game code is executed.

```sh
python3 tools/methods.py SaveGame --image Assembly-CSharp.dll --arch arm64
python3 tools/methods.py GetMouse --arch x86_64 --json
make audit
make setup-scenes
make scenes
.venv/bin/python tools/inspect_scenes.py --scene 6
```

The metadata reader targets the v27 table layout in Unity 2020.3.12f1. It validates table bounds, record strides, type ownership, method tokens, and field/parameter ranges. Type indexes are raw; nested declaring-type resolution, generic instantiations, field offsets, and method bodies remain unresolved.

The native mapper identifies CodeGenModule prefixes by assembly name, maximum method token, and executable pointer validation. It supports the actual `il2cpp` code section. Addresses are unslid virtual addresses. `slice_offset` is relative to the thin architecture slice; `file_offset` is relative to the original universal binary. A zero pointer is recorded as `no_direct_pointer`, without inferring a method's behavior.

Scene inspection uses pinned UnityPy dependencies. It indexes built scenes and exports built-in components for the selected scene under `artifacts/scenes/`. Object references retain Unity file IDs and path IDs. Referenced asset payloads and custom MonoBehaviour data are not exported. Parsing errors are recorded and produce a failing exit status.

Format references: [IL2CPP metadata structures](https://github.com/Perfare/Il2CppDumper/blob/master/Il2CppDumper/Il2Cpp/MetadataClass.cs), [native registration structures](https://github.com/Perfare/Il2CppDumper/blob/master/Il2CppDumper/Il2Cpp/Il2CppClass.cs), [UnityPy](https://github.com/K0lb3/UnityPy). The repository contains an independently written reader, not copied tool source.
