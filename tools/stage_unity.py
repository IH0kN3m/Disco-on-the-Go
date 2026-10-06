#!/usr/bin/env python3
"""Stage a Unity geometry diagnostic from local recovery output, without game scripts."""

import argparse
import json
from pathlib import Path
import shutil

from disco_port.assets import BuiltinResource, local_path, reference_target
from disco_port.binary import FormatError
from disco_port.recovery import validate_geometry
from disco_port.unity_stage import flatten_normals, index_owned_components, validate_parents


ROOT = Path(__file__).resolve().parent.parent


def stage(recovery, scene_export, output, layers=(0, 8)):
    recovery, output = recovery.resolve(), output.resolve()
    if not output.is_relative_to(ROOT / "artifacts"):
        raise FormatError("Stage the Unity project under ignored artifacts/")
    report = json.loads((recovery / "recovery.json").read_text())
    source = json.loads(scene_export.read_text())["scene"]
    if report["errors"] or report["unity_version"] != "2020.3.12f1" or report["scene"] != source["serialized_file"]:
        raise FormatError("Expected matching successful Unity 2020.3.12f1 recovery")
    matching = [s for s in report["sources"] if s["file"] == source["serialized_file"]]
    if len(matching) != 1 or matching[0]["sha256"] != source["sha256"]:
        raise FormatError("Scene exports and recovered components have different source hashes")
    records = json.loads((recovery / "components.json").read_text())
    game_objects = {r["path_id"]: r["data"] for r in records if r["type"] == "GameObject"}
    transforms = {r["path_id"]: r["data"] for r in records if r["type"] in ("Transform", "RectTransform")}
    owners, parents = {}, {}
    for identifier, data in transforms.items():
        pointer = data["m_GameObject"]
        if pointer["m_FileID"] != 0 or pointer["m_PathID"] not in game_objects:
            raise FormatError("Transform GameObject ownership is unresolved")
        owners[identifier] = pointer["m_PathID"]
        if data["m_Father"]["m_FileID"] != 0:
            raise FormatError("Cross-file transform parents are unsupported")
        parents[identifier] = data["m_Father"]["m_PathID"] or None
    if len(set(owners.values())) != len(owners):
        raise FormatError("GameObject has multiple transforms")
    validate_parents(parents)
    mesh_exports = {(e["file"], e["path_id"]): e for e in report["exports"] if e["type"] == "Mesh"}
    material_names = {(e["file"], e["path_id"]): e["name"] for e in report["exports"] if e["type"] == "Material"}
    meshes = []
    for (file, path_id), export in mesh_exports.items():
        data = json.loads(local_path(recovery, export["asset"]).read_text())
        validate_geometry(data["vertices"], data["submeshes"])
        normals = flatten_normals(data.get("normals"), len(data["vertices"]))
        meshes.append({"key": f"{file}:{path_id}",
                       "vertices": [v for p in data["vertices"] for v in p[:3]],
                       "normals": normals,
                       "submeshes": [{"indices": [i for t in triangles for i in t]} for triangles in data["submeshes"]]})
    filters = index_owned_components(records, "MeshFilter", game_objects)
    renderers = index_owned_components(records, "MeshRenderer", game_objects)
    nodes, omissions = [], []
    for identifier, transform in transforms.items():
        owner = owners[identifier]
        game_object = game_objects[owner]
        layer = game_object["m_Layer"]
        if type(layer) is not int or not 0 <= layer < 32:
            raise FormatError("GameObject layer must be 0..31")
        renderer = renderers.get(owner, {})
        visible_material = False
        for pointer in renderer.get("m_Materials", []):
            try:
                target = reference_target(report["scene"], source["external_asset_paths"], pointer)
                if target is not None:
                    if target not in material_names:
                        raise FormatError(f"Material has no recovered export: {target}")
                    visible_material |= material_names[target].lower() != "shadowcaster"
            except BuiltinResource:
                visible_material = True
        node = {"id": owner, "parent": owners[parents[identifier]] if parents[identifier] else -1,
                "name": game_object["m_Name"], "active": bool(game_object["m_IsActive"]),
                "position": transform["m_LocalPosition"], "rotation": transform["m_LocalRotation"],
                "scale": transform["m_LocalScale"], "mesh": "", "render": layer in layers and bool(renderer.get("m_Enabled", False)) and visible_material}
        if owner in filters:
            try:
                target = reference_target(report["scene"], source["external_asset_paths"], filters[owner]["m_Mesh"])
                if target:
                    if target not in mesh_exports:
                        raise FormatError(f"Mesh has no recovered export: {target}")
                    node["mesh"] = f"{target[0]}:{target[1]}"
            except BuiltinResource as error:
                omissions.append({"game_object": owner, "reason": str(error)})
        nodes.append(node)
    assets = output / "Assets"
    (assets / "Resources").mkdir(parents=True, exist_ok=True)
    (assets / "Editor").mkdir(exist_ok=True)
    (output / "Packages").mkdir(exist_ok=True)
    (output / "ProjectSettings").mkdir(exist_ok=True)
    shutil.copyfile(ROOT / "runtime/UnityHost/SceneProbe.cs", assets / "SceneProbe.cs")
    shutil.copyfile(ROOT / "runtime/UnityHost/Editor/BuildProbe.cs", assets / "Editor/BuildProbe.cs")
    (output / "Packages/manifest.json").write_text('{"dependencies":{"com.unity.modules.imgui":"1.0.0","com.unity.modules.jsonserialize":"1.0.0","com.unity.modules.imageconversion":"1.0.0","com.unity.modules.screencapture":"1.0.0"}}\n')
    (output / "ProjectSettings/ProjectVersion.txt").write_text("m_EditorVersion: 2020.3.12f1\nm_EditorVersionWithRevision: 2020.3.12f1 (b3b2c6512326)\n")
    (assets / "Resources/diagnostic.json").write_text(json.dumps({"nodes": nodes, "meshes": meshes}, allow_nan=False) + "\n")
    manifest = {"scope": "Recovered static geometry with neutral materials and a diagnostic camera. Selected mesh-bearing nodes and their ancestors are explicitly activated for viewing. Game scripts, original shaders, textures, and gameplay are absent.",
                "viewing_policy": {"included_layers": list(layers), "excluded_mesh_instances": sum(bool(n["mesh"]) and not n["render"] for n in nodes),
                                   "note": "Default layers 0 and 8 select Default and Mouse Raycast in the supplied build, omitting FOW (13) and Hidden (31) helper surfaces. Null-material and shadowcaster-only renderers are excluded. This is a diagnostic selection, not recovered activation behavior."},
                "scene": report["scene"], "source_sha256": source["sha256"], "nodes": len(nodes), "meshes": len(meshes),
                "mesh_instances": sum(bool(n["mesh"]) and n["render"] for n in nodes), "omissions": omissions}
    (output / "staging.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Staged {len(nodes)} nodes and {len(meshes)} meshes; {len(omissions)} built-in mesh references omitted")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recovery", type=Path, default=ROOT / "artifacts/recovery/scene-06")
    parser.add_argument("--scene-export", type=Path, default=ROOT / "artifacts/scenes/scene-06.json")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/recovered-unity")
    parser.add_argument("--layers", type=int, nargs="+", default=[0, 8], choices=range(32), help="Explicit diagnostic viewing layer selection")
    args = parser.parse_args()
    try:
        stage(args.recovery, args.scene_export, args.output, tuple(dict.fromkeys(args.layers)))
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f"Unity staging failed: {error}\n")


if __name__ == "__main__":
    main()
