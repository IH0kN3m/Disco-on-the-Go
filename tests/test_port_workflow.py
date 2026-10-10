from pathlib import Path
import tempfile
import unittest
from port import steps, source_snapshot


class PortWorkflowTests(unittest.TestCase):
    def test_android_pipeline_uses_mac_and_no_probe_or_device_steps(self):
        plan = steps(Path('/synthetic'), 'android')
        self.assertEqual([name for name, _ in plan], [
            'export-unity-android', 'android-assets', 'android-asset-audit', 'android-build'])
        commands = str(plan)
        for forbidden in ('deploy', 'setup_', 'inspect_scenes', 'recover', 'disco-win', 'build_android.py', 'methods.sqlite'):
            self.assertNotIn(forbidden, commands)
        self.assertIn('/synthetic/.venv/bin/python', commands)
        self.assertIn('--game-data', commands)
        self.assertIn('--obb', commands)
        with self.assertRaises(ValueError): steps(platform='unknown')

    def test_pipeline_order_has_no_device_network_or_recovery_dependencies(self):
        plan = steps(Path('/synthetic'))
        names = [name for name, _ in plan]
        for first, second in [('export-unity', 'engine'), ('amplify', 'configure'), ('engine', 'startup-bundles'),
                              ('addressable-bundles', 'configure'), ('configure', 'native-bc'), ('native-bc', 'build')]:
            self.assertLess(names.index(first), names.index(second))
        commands = str(plan)
        for forbidden in ('deploy_ipad', 'recover_scene', 'inspect_scenes', 'setup_unity', 'pip install'):
            self.assertNotIn(forbidden, commands)
        self.assertNotIn('--diagnostics', commands)

    def test_snapshot_detects_changes_and_rejects_external_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); bundle = root / 'app'; bundle.mkdir()
            (bundle / 'data').write_bytes(b'original')
            snapshot = source_snapshot(bundle)
            self.assertEqual(source_snapshot(bundle), snapshot)
            (bundle / 'data').write_bytes(b'changed')
            self.assertNotEqual(source_snapshot(bundle), snapshot)
            (bundle / 'link').symlink_to(root)
            with self.assertRaises(ValueError): source_snapshot(bundle)
