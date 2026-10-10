from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parent.parent


class AmplifyCoordinatesTests(unittest.TestCase):
    def test_only_owned_gl_coordinate_branches_are_adapted(self):
        directory = ROOT / 'artifacts/tests/amplify-coordinates'
        directory.mkdir(parents=True, exist_ok=True)
        source = directory / 'test.cpp'
        source.write_text(r'''
#include "AmplifyCoordinates.h"
#include <cassert>
#include <initializer_list>
int main() {
    using DiscoAmplifyCoordinates::DeviceType;
    for (uintptr_t site : {uintptr_t(0x1af6430), uintptr_t(0x156af68)}) {
        assert(DeviceType(11,site)==17);
        assert(DeviceType(17,site)==17);
        assert(DeviceType(16,site)==16);
        assert(DeviceType(21,site)==21);
        assert(DeviceType(11,site-4)==11);
        assert(DeviceType(11,site+4)==11);
    }
    assert(DeviceType(11,0)==11);
    assert(DeviceType(11,uintptr_t(-1))==11);
}
''')
        executable = directory / 'test'
        subprocess.run(['xcrun', 'clang++', '-std=c++17', '-I', str(ROOT / 'runtime/AndroidHost'),
                        str(source), '-o', str(executable)], check=True, capture_output=True)
        subprocess.run([str(executable)], check=True, capture_output=True)
