"""Resolve Unity references in the owning serialized file, with bounded streams."""

from pathlib import Path, PurePosixPath

from .binary import FormatError


class BuiltinResource(FormatError):
    """A Unity runtime resource absent from the standalone data directory."""


def local_path(root, name):
    root = Path(root).resolve()
    path = PurePosixPath(name)
    if not name or "\\" in name or path.is_absolute() or ".." in path.parts or ":" in name:
        raise FormatError(f"Unsupported asset path: {name!r}")
    candidate = root.joinpath(*path.parts).resolve()
    if not candidate.is_relative_to(root):
        raise FormatError(f"Asset path escapes data directory: {name!r}")
    return candidate


def reference_target(owner, externals, pointer):
    file_id, path_id = pointer["m_FileID"], pointer["m_PathID"]
    if type(file_id) is not int or type(path_id) is not int:
        raise FormatError("PPtr identifiers must be integers")
    if file_id < 0 or file_id > len(externals) or not -(2**63) <= path_id < 2**63:
        raise FormatError("PPtr identifiers outside supported bounds")
    if path_id == 0:
        return None
    name = owner if file_id == 0 else externals[file_id - 1]
    if name in ("Library/unity default resources", "Resources/unity_builtin_extra"):
        raise BuiltinResource(name)
    return name, path_id


def pointers(value, location="$", depth=0):
    if depth > 128:
        raise FormatError("Serialized object nesting exceeds 128 levels")
    if isinstance(value, dict):
        if set(value) == {"m_FileID", "m_PathID"}:
            yield location, value
        else:
            for key, item in value.items():
                yield from pointers(item, f"{location}.{key}", depth + 1)
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            yield from pointers(item, f"{location}[{index}]", depth + 1)


def stream_bytes(root, name, offset, size, limit=256 * 1024 * 1024):
    if type(offset) is not int or type(size) is not int or offset < 0 or size < 0 or size > limit:
        raise FormatError("Invalid or oversized resource span")
    path = local_path(root, name)
    with path.open("rb") as stream:
        stream.seek(0, 2)
        if offset + size > stream.tell():
            raise FormatError(f"Resource span exceeds {name!r}")
        stream.seek(offset)
        data = stream.read(size)
    if len(data) != size:
        raise FormatError("Resource truncated while reading")
    return data


class AssetStore:
    def __init__(self, root):
        import UnityPy
        if UnityPy.__version__ != "1.25.4":
            raise FormatError("Expected UnityPy 1.25.4; run make setup-scenes")
        self.root = Path(root).resolve()
        self.environment = UnityPy.Environment(path=str(self.root))
        self.files = {}

    def load(self, name):
        if name not in self.files:
            path = local_path(self.root, name)
            if path.stat().st_size > 256 * 1024 * 1024:
                raise FormatError(f"Serialized file exceeds inspection limit: {name}")
            file = self.environment.load_file(path.read_bytes(), name=name)
            if file is None or not hasattr(file, "objects"):
                raise FormatError(f"Expected serialized file: {name}")
            if file.header.version != 22 or file.unity_version != "2020.3.12f1":
                raise FormatError(f"Unsupported serialized layout/version: {name}")
            self.files[name] = file
        return self.files[name]

    def resolve(self, owner, pointer):
        file = self.load(owner)
        target = reference_target(owner, [e.path for e in file.externals], pointer)
        if target is None:
            return None
        name, path_id = target
        file = self.load(name)
        if path_id not in file.objects:
            raise FormatError(f"Missing object {path_id} in {name}")
        return name, file.objects[path_id]
