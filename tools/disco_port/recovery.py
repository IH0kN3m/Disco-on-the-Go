"""Static script layouts and diagnostic geometry; no executable method recovery."""

import math
from importlib.metadata import version

from .binary import FormatError, MachO
from .metadata import Metadata


def type_tree_generator(bundle, backend="AssetsTools"):
    if version("TypeTreeGeneratorAPI") != "0.0.10":
        raise FormatError("Expected TypeTreeGeneratorAPI 0.0.10; run make setup-scenes")
    from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator

    class Generator(TypeTreeGenerator):
        def get_nodes(self, assembly, fullname):
            # UnityPy 1.25.4 adds .dll, while API 0.0.10 indexes extensionless names.
            nodes = super().get_nodes(assembly.removesuffix(".dll"), fullname)
            if not 9 <= len(nodes) <= 100_000 or [n.m_Name for n in nodes[1:9]] != [
                "m_GameObject", "m_FileID", "m_PathID", "m_Enabled", "m_Script", "m_FileID", "m_PathID", "m_Name"
            ]:
                raise FormatError("Unsupported generated MonoBehaviour header")
            # API 0.0.10 omits the alignment flag after the byte-sized enabled
            # field. Unity 2020.3's canonical MonoBehaviour tree aligns it to 4.
            nodes[4].m_MetaFlag |= 0x4000
            return nodes

    binary = (bundle / "Contents/Frameworks/GameAssembly.dylib").read_bytes()
    metadata = (bundle / "Contents/Resources/Data/il2cpp_data/Metadata/global-metadata.dat").read_bytes()
    Metadata(metadata)  # Validate the supported v27 tables before invoking the native backend.
    slice_data = MachO(binary, "arm64").data
    generator = Generator("2020.3.12f1", generator=backend)
    # The backend parses byte buffers. It never loads the game as a native library.
    generator.load_il2cpp(slice_data, metadata)
    return generator


def validate_geometry(vertices, submeshes):
    if not isinstance(vertices, (list, tuple)) or not vertices or len(vertices) > 1_000_000:
        raise FormatError("Unsupported vertex count")
    if any(not isinstance(v, (list, tuple)) or len(v) < 3 or
           not all(type(x) in (int, float) and math.isfinite(x) for x in v[:3]) for v in vertices):
        raise FormatError("Invalid mesh vertex")
    if not isinstance(submeshes, (list, tuple)):
        raise FormatError("Invalid submesh collection")
    count = 0
    for triangles in submeshes:
        if not isinstance(triangles, (list, tuple)):
            raise FormatError("Invalid triangle collection")
        count += len(triangles)
        if count > 2_000_000:
            raise FormatError("Unsupported triangle count")
        for triangle in triangles:
            if not isinstance(triangle, (list, tuple)) or len(triangle) != 3 or any(type(i) is not int or not 0 <= i < len(vertices) for i in triangle):
                raise FormatError("Mesh index outside vertex buffer")
