#!/usr/bin/env python3
"""Recover script values, resolve references, and export diagnostic scene assets."""

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

from disco_port.assets import AssetStore, BuiltinResource, pointers, stream_bytes
from disco_port.binary import FormatError
from disco_port.recovery import type_tree_generator, validate_geometry


def save(path, data):
    def safe(value):
        if isinstance(value, float) and not math.isfinite(value):
            return {"$float": "NaN" if math.isnan(value) else ("Infinity" if value > 0 else "-Infinity")}
        if isinstance(value, dict):
            return {k: safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [safe(v) for v in value]
        return value
    path.write_text(json.dumps(safe(data), indent=2, allow_nan=False) + "\n")


def recover(bundle, output, scene_number):
    from UnityPy.helpers.MeshHelper import MeshHandler
    from UnityPy.export.Texture2DConverter import parse_image_data

    bundle, output = bundle.resolve(), output.resolve()
    if bundle == output or bundle in output.parents:
        raise FormatError("Output must be outside the reference app")
    if not 0 <= scene_number < 36:
        raise FormatError("This build has scene indices 0..35")
    output.mkdir(parents=True, exist_ok=True)
    for name in ("schemas", "meshes", "textures"):
        (output / name).mkdir(exist_ok=True)
    store = AssetStore(bundle / "Contents/Resources/Data")
    owner = f"level{scene_number}"
    scene = store.load(owner)
    generators = {"AssetsTools": type_tree_generator(bundle, "AssetsTools")}
    records, errors, edges = [], [], []
    scripts = Counter()
    schemas = {}
    candidates = {}
    supported = {"GameObject", "Transform", "RectTransform", "Camera", "Light", "MeshFilter", "MeshRenderer", "SkinnedMeshRenderer"}
    for obj in scene.objects.values():
        if obj.type.name not in supported | {"MonoBehaviour"}:
            continue
        record = {"path_id": obj.path_id, "type": obj.type.name}
        try:
            if obj.type.name == "MonoBehaviour":
                head = obj.parse_monobehaviour_head()
                script = store.resolve(owner, {"m_FileID": head.m_Script.m_FileID, "m_PathID": head.m_Script.m_PathID})
                if script is None or script[1].type.name != "MonoScript":
                    raise FormatError("MonoBehaviour script pointer does not resolve to MonoScript")
                script = script[1].parse_as_dict()
                fullname = ".".join(x for x in (script["m_Namespace"], script["m_ClassName"]) if x)
                assembly = script["m_AssemblyName"]
                record["script"] = {"assembly": assembly, "class": fullname}
                expected_head = {"m_GameObject": {"m_FileID": head.m_GameObject.m_FileID, "m_PathID": head.m_GameObject.m_PathID},
                                 "m_Script": {"m_FileID": head.m_Script.m_FileID, "m_PathID": head.m_Script.m_PathID},
                                 "m_Enabled": head.m_Enabled, "m_Name": head.m_Name}
                attempts = []
                for backend in ("AssetsTools", "AssetStudio"):
                    if backend not in generators:
                        generators[backend] = type_tree_generator(bundle, backend)
                    generator = generators[backend]
                    try:
                        data = obj.parse_as_dict(generator.get_nodes_up(assembly, fullname))
                        if any(data.get(k) != v for k, v in expected_head.items()):
                            raise FormatError("Generated script header disagrees with canonical Unity header")
                    except (ValueError, AssertionError, EOFError) as error:
                        attempts.append(f"{backend}: {error}")
                        continue
                    key = (backend, assembly, fullname)
                    if key not in schemas:
                        nodes = generator.get_nodes(assembly, fullname)
                        if not nodes or len(nodes) > 100_000:
                            raise FormatError("Invalid generated type tree size")
                        filename = f"{len(schemas):04}.json"
                        save(output / "schemas" / filename, {"backend": backend, "assembly": assembly,
                             "class": fullname, "nodes": [vars(n) for n in nodes]})
                        schemas[key] = filename
                    record.update(data=data, schema="schemas/" + schemas[key], backend=backend)
                    break
                else:
                    raise FormatError("; ".join(attempts))
                scripts[f"{assembly}:{fullname}"] += 1
            else:
                record["data"] = obj.parse_as_dict()
            records.append(record)
            for location, pointer in pointers(record["data"]):
                edge = {"owner": owner, "object": obj.path_id, "field": location, "pointer": pointer}
                try:
                    target = store.resolve(owner, pointer)
                    if target is None:
                        continue
                    name, destination = target
                    edge.update(target_file=name, target_path_id=destination.path_id, target_type=destination.type.name)
                    if destination.type.name in ("Mesh", "Material"):
                        candidates[(name, destination.path_id)] = destination
                except BuiltinResource as error:
                    edge["runtime_resource"] = str(error)
                except (ValueError, OSError, KeyError) as error:
                    edge["error"] = str(error)
                    errors.append({"stage": "reference", **edge})
                edges.append(edge)
        except (ValueError, AssertionError, OSError, KeyError, EOFError) as error:
            errors.append({"stage": "component", **record, "error": str(error)})

    exports = []
    # One material dependency pass captures its shader and standard texture slots.
    for (name, path_id), obj in list(candidates.items()):
        if obj.type.name != "Material":
            continue
        try:
            data = obj.parse_as_dict()
            asset = f"material-{Path(name).stem}-{path_id}.json"
            save(output / asset, data)
            for location, pointer in pointers(data):
                try:
                    target = store.resolve(name, pointer)
                    if target and target[1].type.name == "Texture2D":
                        candidates[(target[0], target[1].path_id)] = target[1]
                except BuiltinResource:
                    continue
            exports.append({"type": "Material", "file": name, "path_id": path_id, "name": data["m_Name"], "asset": asset})
        except (ValueError, OSError, KeyError) as error:
            errors.append({"stage": "material", "file": name, "path_id": path_id, "error": str(error)})

    for (name, path_id), obj in candidates.items():
        if obj.type.name not in ("Mesh", "Texture2D"):
            continue
        try:
            parsed = obj.parse_as_object()
            filename = f"{Path(name).stem}-{path_id}"
            entry = {"type": obj.type.name, "file": name, "path_id": path_id, "name": parsed.m_Name}
            if obj.type.name == "Mesh":
                stream = parsed.m_StreamData
                if stream and stream.path:
                    payload = stream_bytes(store.root, stream.path, stream.offset, stream.size)
                    entry["stream_source"] = {"file": stream.path, "offset": stream.offset, "size": stream.size,
                                              "sha256": hashlib.sha256(payload).hexdigest()}
                    parsed.m_VertexData.m_DataSize = payload
                    stream.path = ""  # Only this in-memory object changes; no source writes.
                mesh = MeshHandler(parsed)
                mesh.process()
                triangles = mesh.get_triangles()
                validate_geometry(mesh.m_Vertices, triangles)
                asset = f"meshes/{filename}.json"
                save(output / asset, {"coordinate_system": "Unity local coordinates; no handedness conversion",
                    "vertices": mesh.m_Vertices, "normals": mesh.m_Normals, "uv0": mesh.m_UV0, "submeshes": triangles})
                entry.update(asset=asset, vertices=len(mesh.m_Vertices), triangles=sum(map(len, triangles)))
            else:
                width, height = parsed.m_Width, parsed.m_Height
                if not 0 < width <= 8192 or not 0 < height <= 8192 or width * height > 32_000_000:
                    raise FormatError("Unsupported texture dimensions")
                data = parsed.image_data
                if not data:
                    stream = parsed.m_StreamData
                    if not stream or not stream.path:
                        raise FormatError("Texture has no payload")
                    data = stream_bytes(store.root, stream.path, stream.offset, stream.size)
                    entry["stream_source"] = {"file": stream.path, "offset": stream.offset, "size": stream.size,
                                              "sha256": hashlib.sha256(data).hexdigest()}
                image = parse_image_data(bytes(data), width, height, parsed.m_TextureFormat, obj.version, obj.platform,
                                         getattr(parsed, "m_PlatformBlob", None), True)
                asset = f"textures/{filename}.png"
                image.save(output / asset)
                entry.update(asset=asset, width=width, height=height, unity_format=parsed.m_TextureFormat)
            exports.append(entry)
        except (ValueError, AssertionError, OSError, KeyError) as error:
            errors.append({"stage": "asset", "file": name, "path_id": path_id, "type": obj.type.name, "error": str(error)})

    save(output / "components.json", records)
    save(output / "references.json", edges)
    report = {"schema_version": 1, "scene": owner, "unity_version": "2020.3.12f1",
        "scope": "Static serialized values and diagnostic assets. Executable gameplay and shaders are not recovered.",
        "type_tree_backend": "TypeTreeGeneratorAPI 0.0.10 / AssetsTools with AssetStudio fallback",
        "backend_components": dict(Counter(r["backend"] for r in records if "backend" in r)),
        "script_components": sum(scripts.values()), "script_classes": dict(sorted(scripts.items())),
        "schemas": len(schemas), "components": len(records), "references": len(edges),
        "runtime_resource_references": sum("runtime_resource" in e for e in edges),
        "il2cpp_sources": [{"file": str(p), "sha256": hashlib.sha256((bundle / p).read_bytes()).hexdigest()}
                           for p in (Path("Contents/Frameworks/GameAssembly.dylib"),
                                     Path("Contents/Resources/Data/il2cpp_data/Metadata/global-metadata.dat"))],
        "sources": [{"file": n, "sha256": hashlib.sha256((store.root / n).read_bytes()).hexdigest()} for n in sorted(store.files)],
        "exports": exports, "errors": errors}
    save(output / "recovery.json", report)
    print(f"{owner}: {sum(scripts.values())} script components, {len(schemas)} schemas, {dict(Counter(e['type'] for e in exports))}, {len(errors)} unresolved errors")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=Path("reference/Disco.app"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/recovery/scene-06"))
    parser.add_argument("--scene", type=int, default=6)
    args = parser.parse_args()
    try:
        report = recover(args.bundle, args.output, args.scene)
    except (ValueError, OSError, ImportError, AssertionError) as error:
        parser.exit(1, f"Scene recovery failed: {error}\n")
    if report["errors"]:
        parser.exit(1, "Partial recovery saved; inspect recovery.json for unresolved layouts and dependencies.\n")


if __name__ == "__main__":
    main()
