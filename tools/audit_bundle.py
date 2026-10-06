#!/usr/bin/env python3
"""Read a Unity macOS bundle and emit porting evidence without loading its code.

Uses the Python standard library and macOS nm. Writes only the requested JSON.
This is an inventory, not an IL2CPP decompiler or an asset extractor.
"""

import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import struct
import subprocess


def cstring(data, offset=0):
    end = data.index(b"\0", offset)
    return data[offset:end].decode("utf-8", "replace"), end + 1


def version(value):
    return f"{value >> 16}.{(value >> 8) & 255}.{value & 255}"


def macho(path):
    data = path.read_bytes()
    slices = [(0, len(data))]
    if data[:4] == b"\xca\xfe\xba\xbe":
        count = struct.unpack_from(">I", data, 4)[0]
        slices = [struct.unpack_from(">II", data, 8 + i * 20 + 8) for i in range(count)]
    result = []
    for base, size in slices:
        if data[base:base + 4] != b"\xcf\xfa\xed\xfe":
            continue  # This audit only parses 64-bit little-endian Mach-O slices.
        _, cpu, subtype, filetype, ncmds, _, flags, _ = struct.unpack_from("<8I", data, base)
        item = {"architecture": {0x100000c: "arm64", 0x1000007: "x86_64"}.get(cpu, hex(cpu)),
                "slice_bytes": size, "filetype": filetype, "libraries": [], "rpaths": []}
        cursor = base + 32
        strings = []
        for _ in range(ncmds):
            cmd, length = struct.unpack_from("<II", data, cursor)
            if length < 8 or cursor + length > base + size:
                raise ValueError(f"Invalid load command in {path}")
            if cmd in (0xc, 0x80000018, 0x8000001f, 0x20, 0x80000023):
                offset = struct.unpack_from("<I", data, cursor + 8)[0]
                item["libraries"].append(cstring(data, cursor + offset)[0])
            elif cmd == 0x8000001c:
                offset = struct.unpack_from("<I", data, cursor + 8)[0]
                item["rpaths"].append(cstring(data, cursor + offset)[0])
            elif cmd == 0x32:
                platform, minimum, sdk = struct.unpack_from("<III", data, cursor + 8)
                item["build"] = {"platform_id": platform,
                                  "platform": {1: "macOS", 2: "iOS", 7: "iOS Simulator"}.get(platform, str(platform)),
                                  "minimum_os": version(minimum), "sdk": version(sdk)}
            elif cmd in (0x24, 0x25):
                minimum, sdk = struct.unpack_from("<II", data, cursor + 8)
                item["build"] = {"platform": "macOS" if cmd == 0x24 else "iOS",
                                  "minimum_os": version(minimum), "sdk": version(sdk)}
            elif cmd == 0x19:
                sections = struct.unpack_from("<I", data, cursor + 64)[0]
                for j in range(sections):
                    start = cursor + 72 + j * 80
                    name = data[start:start + 16].split(b"\0")[0]
                    if name == b"__cstring":
                        section_size, offset = struct.unpack_from("<QI", data, start + 40)
                        strings += [s.decode("utf-8", "replace")
                                    for s in data[base + offset:base + offset + section_size].split(b"\0") if s]
            cursor += length
        if item["architecture"] == "arm64":
            item["unity_internal_call_strings"] = sorted(set(s for s in strings if s.startswith("UnityEngine.") and "::" in s))
            for key, options in [("exports", ["-gU"]), ("imports", ["-u"])]:
                completed = subprocess.run(["nm", "-arch", "arm64", *options, str(path)], capture_output=True, text=True)
                if completed.returncode:
                    item[key + "_error"] = completed.stderr.strip()
                else:
                    item[key] = [line.split()[-1] for line in completed.stdout.splitlines() if line.split()]
        result.append(item)
    return result


def asset_header(path):
    with path.open("rb") as handle:
        data = handle.read(256)
    metadata_size, file_size, file_version, data_offset = struct.unpack_from(">IIII", data)
    endian = "<" if data[16] == 0 else ">"
    if file_version >= 22:
        metadata_size, file_size, data_offset = struct.unpack_from(">IQQ", data, 20)
    start = 48 if file_version >= 22 else 20
    engine, cursor = cstring(data, start)
    target = struct.unpack_from(endian + "i", data, cursor)[0]
    return {"serialized_version": file_version, "unity_version": engine,
            "target_id": target, "type_trees_present": bool(data[cursor + 4]),
            "metadata_bytes": metadata_size, "declared_file_bytes": file_size,
            "actual_file_bytes": path.stat().st_size, "data_offset": data_offset}


def summarize(paths, root):
    entries = [(p.stat().st_size, str(p.relative_to(root))) for p in paths]
    return {"files": len(entries), "bytes": sum(x[0] for x in entries),
            "largest_files": [{"path": p, "bytes": size} for size, p in sorted(entries, reverse=True)[:10]]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    root = args.bundle.resolve()
    output = args.output.resolve()
    if output == root or root in output.parents:
        parser.error("Output must be outside the reference bundle")
    contents = root / "Contents"
    resources = contents / "Resources/Data"
    files = sorted(p for p in root.rglob("*") if p.is_file())
    with (contents / "Info.plist").open("rb") as handle:
        info = plistlib.load(handle)
    audit = {"bundle": str(root), "info_plist": info, "inventory": summarize(files, root)}
    audit["game_store_info"] = json.loads((contents / "Resources/goggame-1771589310.info").read_text())
    audit["binaries"] = {}
    candidates = sorted(set(contents.rglob("*.dylib")) | set((contents / "MacOS").iterdir()) |
                        {p for p in (contents / "PlugIns").rglob("*") if p.is_file() and p.parent.name == "MacOS"})
    for path in candidates:
        audit["binaries"][str(path.relative_to(root))] = {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "slices": macho(path)}
    metadata_path = resources / "il2cpp_data/Metadata/global-metadata.dat"
    data = metadata_path.read_bytes()
    magic, v = struct.unpack_from("<II", data)
    offset, size = struct.unpack_from("<II", data, 24)
    if magic != 0xfab11baf or offset + size > len(data):
        raise ValueError("Unrecognized metadata header or invalid string heap")
    strings = [s.decode("utf-8", "replace") for s in data[offset:offset + size].split(b"\0") if s]
    audit["il2cpp_metadata"] = {"bytes": len(data), "magic": hex(magic), "version": v,
                               "sha256": hashlib.sha256(data).hexdigest(), "string_heap_bytes": size,
                               "name_searches": {term: {"count": len(matches), "examples": matches[:20]}
                                                 for term in ["touch", "mouse", "input", "savegame", "dialogue", "amplify", "incontrol"]
                                                 for matches in [[s for s in strings if term in s.lower()]]},
                               "limitation": "Names do not establish method behavior or active features"}
    audit["assemblies"] = json.loads((resources / "ScriptingAssemblies.json").read_text())["names"]
    audit["addressables_settings"] = json.loads((resources / "StreamingAssets/aa/settings.json").read_text())
    catalog = json.loads((resources / "StreamingAssets/aa/catalog.json").read_text())
    audit["addressables_catalog"] = {"providers": catalog.get("m_ProviderIds"),
                                     "internal_id_count": len(catalog.get("m_InternalIds", [])),
                                     "internal_id_examples": catalog.get("m_InternalIds", [])[:10]}
    audit["asset_header_samples"] = {name: asset_header(resources / name)
                                     for name in ["globalgamemanagers", "resources.assets", "sharedassets0.assets", "level0", "level1"]}
    audit["data_groups"] = {name: summarize(sorted(p for p in (resources / name).rglob("*") if p.is_file()), resources)
                            for name in ["AmplifyTexture", "StreamingAssets", "StreamingAssets/aa/StandaloneOSX"]}
    audit["scope"] = "Static inspection only; no game code loaded, asset extraction, iPad execution, or performance measurements"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(audit, indent=2) + "\n")
    print(f"Wrote {output}")
    print(f"Bundle: {audit['inventory']['files']} files, {audit['inventory']['bytes']} bytes")
    for name, binary in audit["binaries"].items():
        print(name, [(s["architecture"], s.get("build", {}).get("platform")) for s in binary["slices"]])


if __name__ == "__main__":
    main()
