import tempfile
import unittest
from pathlib import Path

from disco_port.assets import BuiltinResource, local_path, pointers, reference_target, stream_bytes
from disco_port.binary import FormatError
from disco_port.recovery import validate_geometry


class AssetTests(unittest.TestCase):
    def test_geometry_checks_finite_positions_and_index_ownership(self):
        vertices = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
        validate_geometry(vertices, [[(0, 1, 2)]])
        for points, faces in (([], []), ([(float("nan"), 0, 0)], []), (vertices, [[(0, 1, 3)]]),
                              (vertices, [[(0, -1, 2)]]), (vertices, [[(0, True, 2)]]), (vertices, [[(0, 1)]]),
                              ([(0, 0, "bad")], []), ([None], []), (vertices, [None]), (vertices, [[None]])):
            with self.assertRaises(FormatError):
                validate_geometry(points, faces)

    def test_pointer_uses_owner_and_one_based_external_table(self):
        p = {"m_FileID": 0, "m_PathID": 42}
        self.assertEqual(reference_target("level6", ["shared.assets"], p), ("level6", 42))
        p["m_FileID"] = 1
        self.assertEqual(reference_target("level6", ["shared.assets"], p), ("shared.assets", 42))
        self.assertEqual(reference_target("other.assets", ["different.assets"], p), ("different.assets", 42))

    def test_null_negative_path_id_and_invalid_identifiers(self):
        self.assertIsNone(reference_target("a", [], {"m_FileID": 0, "m_PathID": 0}))
        self.assertEqual(reference_target("a", [], {"m_FileID": 0, "m_PathID": -2}), ("a", -2))
        for file_id, path_id in ((-1, 1), (1, 1), (0, 2**63), (True, 1), (0, "1")):
            with self.assertRaises(FormatError):
                reference_target("a", [], {"m_FileID": file_id, "m_PathID": path_id})

    def test_runtime_resources_are_explicit(self):
        with self.assertRaises(BuiltinResource):
            reference_target("a", ["Library/unity default resources"], {"m_FileID": 1, "m_PathID": 1})

    def test_nested_pointer_locations(self):
        p = {"m_FileID": 0, "m_PathID": 7}
        self.assertEqual(list(pointers({"items": [p, {"m_FileID": 5}]})), [("$.items[0]", p)])
        self.assertEqual(list(pointers([("texture", p)])), [("$[0][1]", p)])
        deep = p
        for _ in range(130):
            deep = [deep]
        with self.assertRaises(FormatError):
            list(pointers(deep))

    def test_path_traversal_and_symlinks_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "data"
            root.mkdir()
            self.assertEqual(local_path(root, "a/b"), root.resolve() / "a/b")
            for name in ("", "../out", "/etc/passwd", "a/../../out", "archive:/a", "a\\b"):
                with self.assertRaises(FormatError):
                    local_path(root, name)
            (root / "link").symlink_to(Path(directory))
            with self.assertRaises(FormatError):
                local_path(root, "link/out")

    def test_stream_span_exact_and_malformed(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "a.resS").write_bytes(b"012345")
            self.assertEqual(stream_bytes(directory, "a.resS", 2, 3), b"234")
            self.assertEqual(stream_bytes(directory, "a.resS", 6, 0), b"")
            for offset, size in ((-1, 1), (0, -1), (5, 2), (7, 0), (0, 100), (True, 1)):
                with self.assertRaises(FormatError):
                    stream_bytes(directory, "a.resS", offset, size, limit=8)
