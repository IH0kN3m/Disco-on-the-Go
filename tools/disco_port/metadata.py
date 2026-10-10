"""Read the v27 metadata tables used by Unity 2020.3.12f1.

Field order is documented by IL2CPP metadata structures; validated against the supplied version.
Type indexes remain raw until native metadata registration is recovered.
"""

from .binary import FormatError, read_string, unpack


class Metadata:
    def __init__(self, data):
        self.data = data
        magic, version = unpack(data, "<II", 0)
        if magic != 0xfab11baf or version != 27:
            raise FormatError("This reader requires the standard IL2CPP v27 layout")
        self.version = version
        self.tables = {}
        for name, index, stride in [("strings", 2, 1), ("methods", 5, 32), ("parameters", 10, 12),
                                    ("fields", 11, 12), ("types", 19, 88), ("images", 20, 40)]:
            offset, size = unpack(data, "<II", 8 + index * 8)
            if offset < 256 or offset + size > len(data) or size % stride:
                raise FormatError(f"Invalid {name} table")
            self.tables[name] = (offset, size, stride)
        self.images = []
        self.types = []
        self.methods = []
        self.fields = []
        self.parameters = []
        for row in self.rows("images", "<IiIiIiiIiI"):
            self.images.append({"name": self.string(row[0]), "type_start": row[2], "type_count": row[3], "max_method_rid": 0})
        for index, row in enumerate(self.rows("types", "<IIiiiiiI8i8HII")):
            self.types.append({"index": index, "name": self.string(row[0]), "namespace": self.string(row[1]),
                               "byval_type_index": row[2], "declaring_type_index": row[3],
                               "flags": row[7], "field_start": row[8], "method_start": row[9],
                               "method_count": row[16], "field_count": row[18], "token": row[-1]})
        owners = [None] * len(self.types)
        for image in self.images:
            start, count = image["type_start"], image["type_count"]
            if start < 0 or start + count > len(self.types):
                raise FormatError("Image type range is outside metadata")
            for i in range(start, start + count):
                if owners[i] is not None:
                    raise FormatError("Overlapping image type ranges")
                owners[i] = image
        if any(o is None for o in owners):
            raise FormatError("Some types have no owning image")
        for index, row in enumerate(self.rows("methods", "<IiiiiI4H")):
            if not 0 <= row[1] < len(self.types) or row[5] >> 24 != 6 or row[5] & 0xffffff == 0:
                raise FormatError("Invalid method owner or metadata token")
            owner = owners[row[1]]
            owner["max_method_rid"] = max(owner["max_method_rid"], row[5] & 0xffffff)
            self.methods.append({"index": index, "name": self.string(row[0]), "type_index": row[1],
                                 "return_type_index": row[2], "parameter_start": row[3],
                                 "generic_container_index": row[4], "token": row[5], "flags": row[6],
                                 "implementation_flags": row[7], "parameter_count": row[9], "image": owner["name"]})
        for index, row in enumerate(self.rows("fields", "<IiI")):
            self.fields.append({"index": index, "name": self.string(row[0]), "type_index": row[1], "token": row[2]})
        for row in self.rows("parameters", "<IIi"):
            self.parameters.append({"name": self.string(row[0]), "token": row[1], "type_index": row[2]})
        for t, owner in zip(self.types, owners):
            t["image"] = owner["name"]
            t["qualified_name"] = (t["namespace"] + "." if t["namespace"] else "") + t["name"]
            for kind in ("method", "field"):
                values = self.methods if kind == "method" else self.fields
                start, count = t[kind + "_start"], t[kind + "_count"]
                if count and (start < 0 or start + count > len(values)):
                    raise FormatError(f"Invalid {kind} range for {t['qualified_name']}")
                if kind == "method" and any(m["type_index"] != t["index"] for m in values[start:start + count] if count):
                    raise FormatError("Type method ownership mismatch")
        for m in self.methods:
            start, count = m["parameter_start"], m["parameter_count"]
            if count and (start < 0 or start + count > len(self.parameters)):
                raise FormatError("Invalid method parameter range")
            m["qualified_name"] = self.types[m["type_index"]]["qualified_name"] + "::" + m["name"]

    def rows(self, name, fmt):
        offset, size, stride = self.tables[name]
        import struct
        if struct.calcsize(fmt) != stride:
            raise FormatError("Record format does not match table stride")
        for at in range(offset, offset + size, stride):
            yield unpack(self.data, fmt, at)

    def string(self, index):
        offset, size, _ = self.tables["strings"]
        if not 0 <= index < size:
            raise FormatError("String index outside metadata heap")
        return read_string(self.data, offset + index, offset + size)
