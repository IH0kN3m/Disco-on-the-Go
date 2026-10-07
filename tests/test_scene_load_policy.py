"""Execute only our original portable policy code, never supplied game code."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parent.parent


class SceneLoadPolicyTests(unittest.TestCase):
    def test_bootstrap_ownership_and_malformed_scene_keys(self):
        output = ROOT / 'artifacts/tests/scene-policy'
        output.mkdir(parents=True, exist_ok=True)
        source = output / 'check.cpp'
        source.write_text(r'''
#include "SceneLoadPolicy.h"
#include <cassert>
int main() {
    using namespace DiscoScenePolicy;
    PreloadPlan p; std::string error;
    assert(Plan({"Assets/Scenes/Init.unity", "Assets/Scenes/RoomA.unity", "Assets/Scenes/RoomB.unity"},
                {"Scenes/Init"}, p, error));
    assert(p.bootstrap == "Scenes/RoomA");
    assert((p.deferred == std::vector<std::string>{"Scenes/Init", "Scenes/RoomB"}));
    assert(!Plan({"Assets/Scenes/a/Room.unity", "Assets/Scenes/b/Room.unity"}, {}, p, error));
    assert(p.bootstrap.empty() && p.deferred.empty());
    assert(!Plan({"Assets/Scenes/Room.unity"}, {"Scenes/Room"}, p, error));
    assert(!Plan({}, {}, p, error));
    assert(!Plan(std::vector<std::string>(257, "Assets/Scenes/Room.unity"), {}, p, error));
    for (const std::string bad : {"../Room.unity", "Assets/Scenes/../Room.unity", "Assets/Scenes//Room.unity",
                                 "Assets/Scenes/./Room.unity", "Assets/Scenes/.unity", "Assets/Scenes/Room.prefab",
                                 "Assets/Scenes\\Room.unity", "Other/Scenes/Room.unity"})
        assert(!Plan({bad}, {}, p, error));
    std::string nul = "Assets/Scenes/Room.unity"; nul.insert(17, 1, '\0');
    assert(!Plan({nul}, {}, p, error));
}
''')
        executable = output / 'check'
        subprocess.run(['xcrun', 'clang++', '-std=c++17', '-I', str(ROOT / 'runtime/UnityHost'),
                        str(source), '-o', str(executable)], check=True, capture_output=True)
        subprocess.run([str(executable)], check=True, capture_output=True)
