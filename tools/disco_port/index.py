"""Build a local, searchable method map from metadata and CodeGenModules."""

import hashlib
import json
from pathlib import Path
import sqlite3

from .binary import MachO
from .metadata import Metadata


def build_index(bundle, destination, architectures=("arm64", "x86_64")):
    bundle, destination = Path(bundle).resolve(), Path(destination).resolve()
    if bundle == destination or bundle in destination.parents:
        raise ValueError("Generated output must be outside the reference app")
    root = bundle / "Contents"
    metadata_bytes = (root / "Resources/Data/il2cpp_data/Metadata/global-metadata.dat").read_bytes()
    binary_bytes = (root / "Frameworks/GameAssembly.dylib").read_bytes()
    metadata = Metadata(metadata_bytes)
    mappings = {}
    summary = {"schema_version": 1, "metadata_sha256": hashlib.sha256(metadata_bytes).hexdigest(),
               "gameassembly_sha256": hashlib.sha256(binary_bytes).hexdigest(),
               "images": len(metadata.images), "types": len(metadata.types), "methods": len(metadata.methods),
               "fields": len(metadata.fields), "architectures": {},
               "scope": "Names, raw type indexes, and unslid native addresses; method bodies are not recovered"}
    for architecture in architectures:
        macho = MachO(binary_bytes, architecture)
        modules = macho.find_modules(metadata.images)
        missing = [i["name"] for i in metadata.images if i["max_method_rid"] and i["name"] not in modules]
        if missing:
            raise ValueError(f"Cannot validate CodeGenModules for {architecture}: {missing}")
        mappings[architecture] = (macho, modules)
    destination.mkdir(parents=True, exist_ok=True)
    temporary = destination / "methods.sqlite.tmp"
    if temporary.exists():
        temporary.unlink()
    try:
        with sqlite3.connect(temporary) as db:
            db.executescript("""
            CREATE TABLE provenance (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE images (name TEXT PRIMARY KEY, type_count INTEGER NOT NULL, max_method_rid INTEGER NOT NULL);
            CREATE TABLE types (id INTEGER PRIMARY KEY, image TEXT NOT NULL, name TEXT NOT NULL, namespace TEXT NOT NULL,
                                qualified_name TEXT NOT NULL, byval_type_index INTEGER NOT NULL, declaring_type_index INTEGER NOT NULL);
            CREATE TABLE methods (id INTEGER PRIMARY KEY, type_id INTEGER NOT NULL, image TEXT NOT NULL, name TEXT NOT NULL,
                                  qualified_name TEXT NOT NULL, token INTEGER NOT NULL, return_type_index INTEGER NOT NULL,
                                  parameter_count INTEGER NOT NULL, flags INTEGER NOT NULL, generic_container_index INTEGER NOT NULL);
            CREATE TABLE parameters (method_id INTEGER NOT NULL, ordinal INTEGER NOT NULL, name TEXT NOT NULL,
                                     type_index INTEGER NOT NULL, PRIMARY KEY(method_id, ordinal));
            CREATE TABLE fields (id INTEGER PRIMARY KEY, type_id INTEGER NOT NULL, name TEXT NOT NULL,
                                 type_index INTEGER NOT NULL, token INTEGER NOT NULL);
            CREATE TABLE locations (method_id INTEGER NOT NULL, architecture TEXT NOT NULL, address INTEGER,
                                    slice_offset INTEGER, file_offset INTEGER, status TEXT NOT NULL,
                                    PRIMARY KEY(method_id, architecture));
            CREATE INDEX methods_image ON methods(image);
            CREATE INDEX methods_type ON methods(type_id);
            CREATE INDEX fields_type ON fields(type_id);
            """)
            db.executemany("INSERT INTO images VALUES (?, ?, ?)", [(i["name"], i["type_count"], i["max_method_rid"]) for i in metadata.images])
            db.executemany("INSERT INTO types VALUES (?, ?, ?, ?, ?, ?, ?)",
                           [(t["index"], t["image"], t["name"], t["namespace"], t["qualified_name"], t["byval_type_index"], t["declaring_type_index"]) for t in metadata.types])
            db.executemany("INSERT INTO methods VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           [(m["index"], m["type_index"], m["image"], m["name"], m["qualified_name"], m["token"], m["return_type_index"],
                             m["parameter_count"], m["flags"], m["generic_container_index"]) for m in metadata.methods])
            db.executemany("INSERT INTO parameters VALUES (?, ?, ?, ?)",
                           [(m["index"], j, p["name"], p["type_index"]) for m in metadata.methods
                            for j, p in enumerate(metadata.parameters[m["parameter_start"]:m["parameter_start"] + m["parameter_count"]] if m["parameter_count"] else [])])
            db.executemany("INSERT INTO fields VALUES (?, ?, ?, ?, ?)",
                           [(f["index"], t["index"], f["name"], f["type_index"], f["token"]) for t in metadata.types
                            for f in (metadata.fields[t["field_start"]:t["field_start"] + t["field_count"]] if t["field_count"] else [])])
            for architecture, (macho, modules) in mappings.items():
                rows = []
                for method in metadata.methods:
                    module = modules.get(method["image"])
                    pointer = module["pointers"][(method["token"] & 0xffffff) - 1] if module else 0
                    offset = macho.offset_for_address(pointer, 4) if pointer else None
                    rows.append((method["index"], architecture, pointer or None, offset,
                                 offset + macho.slice_offset if offset is not None else None,
                                 "mapped" if pointer else "no_direct_pointer"))
                db.executemany("INSERT INTO locations VALUES (?, ?, ?, ?, ?, ?)", rows)
                summary["architectures"][architecture] = {"modules": len(modules), "mapped_methods": sum(row[-1] == "mapped" for row in rows),
                                                           "no_direct_pointer": sum(row[-1] != "mapped" for row in rows)}
            db.executemany("INSERT INTO provenance VALUES (?, ?)", [(key, json.dumps(value)) for key, value in summary.items()])
        temporary.replace(destination / "methods.sqlite")
    finally:
        if temporary.exists():
            temporary.unlink()
    (destination / "inspection.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def search(database, term, image=None, architecture="arm64", limit=25):
    database = Path(database).resolve()
    if not database.is_file():
        raise ValueError(f"Index missing: {database}; run make inspect")
    with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        sql = """SELECT m.id, m.image, m.qualified_name, m.token, m.parameter_count, l.address,
                        l.file_offset, l.status FROM methods m JOIN locations l ON m.id=l.method_id
                 WHERE m.qualified_name LIKE ? ESCAPE '\\' AND l.architecture=?"""
        literal = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        args = ["%" + literal + "%", architecture]
        if image:
            sql += " AND m.image=?"
            args.append(image)
        sql += " ORDER BY m.image, m.qualified_name, m.id LIMIT ?"
        args.append(limit)
        return [dict(row) for row in db.execute(sql, args)]
