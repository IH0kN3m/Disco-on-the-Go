#!/usr/bin/env python3
"""Index built scenes and export built-in components for one recovery target."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def inspect(bundle, output, selected):
    import UnityPy
    if UnityPy.__version__ != "1.25.4":
        raise ValueError("Expected UnityPy 1.25.4; run make setup-scenes")
    bundle, output = bundle.resolve(), output.resolve()
    if bundle == output or bundle in output.parents:
        raise ValueError("Generated output must be outside the reference app")
    root = bundle / "Contents/Resources/Data"
    globals_environment = UnityPy.load((root / "globalgamemanagers").read_bytes())
    settings = [o for o in globals_environment.objects if o.type.name == "BuildSettings"]
    if len(settings) != 1:
        raise ValueError("Expected one BuildSettings object")
    # Only whitelist necessary fields; BuildSettings also contains build tokens.
    settings = settings[0].parse_as_dict()
    paths = settings["scenes"]
    if settings["m_Version"] != "2020.3.12f1":
        raise ValueError("Scene recovery currently targets Unity 2020.3.12f1")
    if not 0 <= selected < len(paths):
        raise ValueError(f"Scene index must be in 0..{len(paths)-1}")
    output.mkdir(parents=True, exist_ok=True)
    index = {"schema_version": 1, "unity_version": settings["m_Version"], "scenes": []}
    supported = {"GameObject", "Transform", "RectTransform", "Camera", "Light", "MeshFilter", "MeshRenderer", "SkinnedMeshRenderer"}
    for number, path in enumerate(paths):
        scene_path = root / f"level{number}"
        data = scene_path.read_bytes()
        environment = UnityPy.load(data)
        objects = list(environment.objects)
        counts = dict(sorted(Counter(o.type.name for o in objects).items()))
        names = []
        errors = []
        components = []
        for obj in objects:
            if obj.type.name == "GameObject":
                try:
                    names.append({"path_id": obj.path_id, "name": obj.peek_name()})
                except Exception as error:
                    errors.append({"path_id": obj.path_id, "type": obj.type.name, "error": str(error)})
            if number == selected and obj.type.name in supported:
                try:
                    components.append({"path_id": obj.path_id, "type": obj.type.name, "data": obj.parse_as_dict()})
                except Exception as error:
                    errors.append({"path_id": obj.path_id, "type": obj.type.name, "error": str(error)})
        externals = [x.path for x in objects[0].assets_file.externals] if objects else []
        entry = {"index": number, "source_scene": path, "serialized_file": scene_path.name,
                 "sha256": hashlib.sha256(data).hexdigest(), "objects": len(objects), "class_counts": counts,
                 "external_asset_paths": externals, "game_objects": names, "errors": errors}
        index["scenes"].append(entry)
        if number == selected:
            hierarchy = {"schema_version": 1, "scene": entry, "components": components,
                         "scope": "Built-in component values and references only; custom scripts, meshes, textures, shaders, and gameplay are not recovered"}
            (output / f"scene-{number:02}.json").write_text(json.dumps(hierarchy, indent=2) + "\n")
        print(f"{number:02}  {len(objects):5} objects  {Path(path).stem}  {len(errors)} parsing errors")
    (output / "scenes.json").write_text(json.dumps(index, indent=2) + "\n")
    failures = sum(len(s["errors"]) for s in index["scenes"])
    if failures:
        raise ValueError(f"Saved partial results with {failures} parsing errors; inspect scenes.json")
    return index


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=Path("reference/Disco.app"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/scenes"))
    parser.add_argument("--scene", type=int, default=6, help="Build index of the scene to export; default is Whirling floor 2")
    args = parser.parse_args()
    try:
        inspect(args.bundle, args.output, args.scene)
    except (ImportError, OSError, ValueError) as error:
        parser.exit(1, f"Scene inspection failed: {error}\n")


if __name__ == "__main__":
    main()
