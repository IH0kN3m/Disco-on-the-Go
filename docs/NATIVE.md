# Native runtime probe

The supplied ARM64 GameAssembly exports 232 IL2CPP entry points and imports 334 symbols. The CPU probe derives an iOS framework from that module, preserves its executable sections byte for byte, and uses the original metadata. No reference binary is loaded on the Mac or changed in place.

```sh
make prepare-runtime-probe
make deploy-runtime-probe
```

Requires Xcode, the supplied app, and the existing ignored `artifacts/local-ipad.json` device/team configuration. Unity editor installation is not required for this CPU check. Preparation validates Mach-O bounds, dynamic-library type, build platform, dependency paths, executable address/offset ownership, metadata v27, and output code hashes. It removes the derived copy's old signature, sets its iOS loader platform, rewrites the three versioned Apple framework paths, and changes its install name. Xcode development-signs the embedded framework and app. Only the explicitly enabled device build includes game bytes; normal touch-harness builds skip them. Prepared module/metadata hashes are checked before embedding.

Actual result on 7 October 2026: the physical stock 13-inch M4 loaded the derived module, initialized the original IL2CPP runtime/metadata, resolved `UnityEngine.Vector3.Dot` through the original runtime API, and invoked it with `(1,2,3)` and `(4,5,6)`. The boxed result was **32**. Log: `Documents/native-runtime.log` in the `org.discoport.runtimeprobe` app container; retrieved output stays under `artifacts/runtime-probe/`.

This proves this native CPU/runtime check. It does not establish Unity engine bindings, game-specific method behavior, plugin compatibility, asset/shader compatibility, touch integration, or gameplay. The probe keeps the runtime loaded for the process lifetime and does not start the game. The next integration experiment is replacing the diagnostic player's IL2CPP provider with the original module and registering the Unity native bindings it needs.

Static follow-up: the exported Unity 2020.3.12f1 iOS engine archive references 161 unique IL2CPP C APIs; the original module exports all 161. Its additional `Unity_il2cppNoExceptions` reference is supplied by the generated player options source. This checks symbol coverage only. The exported diagnostic currently registers a stripped subset of Unity bindings and links its own `libil2cpp.a`; an engine experiment must select one runtime provider, use matching metadata, and establish the required bindings before gameplay can be assessed. The audit listings remain under `artifacts/linkage/`.

Never commit the derived framework, original metadata, native export/import listings, signing data, or device logs. The repository contains only the original preparation, host, and validation code.
