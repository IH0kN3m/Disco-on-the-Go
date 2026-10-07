from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parent.parent


class TouchControlPolicyTests(unittest.TestCase):
    def test_camera_ownership_conflicts_invalid_scales_and_key_cancellation(self):
        directory = ROOT / 'artifacts/tests/touch-controls'
        directory.mkdir(parents=True, exist_ok=True)
        source = directory / 'test.cpp'
        source.write_text(r'''
#include "TouchControlPolicy.h"
#include <cassert>
#include <limits>
#include <initializer_list>
int main() {
    float x,y;
    assert(DiscoTouch::Stick(0,0,50,x,y) && x == 0 && y == 0);
    assert(DiscoTouch::Stick(3,0,50,x,y) && x == 0); // Dead zone.
    assert(DiscoTouch::Stick(25,-25,50,x,y) && x == 0.5f && y == -0.5f);
    assert(DiscoTouch::Stick(500,500,50,x,y) && std::fabs(x*x+y*y-1)<0.00001f);
    assert(DiscoTouch::Stick(-500,0,50,x,y) && x == -1 && y == 0);
    assert(!DiscoTouch::Stick(1,2,0,x,y) && x == 0 && y == 0);
    assert(!DiscoTouch::Stick(std::numeric_limits<float>::infinity(),2,50,x,y));
    DiscoTouch::Pinch pinch;
    float delta = 17;
    assert(!pinch.Change(1, true, 2, delta) && delta == 0);
    assert(!pinch.Begin(0, true, 1));
    assert(!pinch.Begin(1, false, 1)); // UI/locked camera.
    assert(pinch.Begin(1, true, 1));
    assert(pinch.Change(1, true, 2, delta) && std::fabs(delta + 0.25f) < 0.00001f);
    assert(pinch.Change(1, true, 1, delta) && std::fabs(delta - 0.25f) < 0.00001f);
    assert(!pinch.Change(2, true, 1, delta)); // Area/camera switched mid-pinch.
    assert(!pinch.Change(1, true, 1, delta)); // Owner cancellation persists.
    assert(pinch.Begin(2, true, 1));
    assert(!pinch.Change(2, false, 2, delta)); // Dialogue lock began.
    for (double scale : {0., -1., 10001., std::numeric_limits<double>::infinity(), std::numeric_limits<double>::quiet_NaN()})
        assert(!pinch.Begin(2, true, scale));
    assert(pinch.Begin(2, true, 1));
    pinch.Cancel();
    assert(!pinch.Change(2, true, 2, delta));
    DiscoTouch::Keys keys;
    assert(keys.Set(1, true));
    assert(!keys.Set(1, true)); // Repeated UIKit down cannot duplicate a press.
    assert(keys.Set(3, true));
    assert(!keys.Set(32, true));
    assert(keys.Set(1, false)); // Outside/cancel is the same release.
    assert(!keys.Set(1, false));
    assert(keys.Cancel() == 8); // Hide/suspend releases all remaining keys.
    assert(keys.Cancel() == 0);
    assert(keys.Set(31, true) && keys.Cancel() == 0x80000000u);
}
''')
        executable = directory / 'test'
        subprocess.run(['xcrun', 'clang++', '-std=c++17', '-I', str(ROOT / 'runtime/UnityHost'),
                        str(source), '-o', str(executable)], check=True, capture_output=True)
        subprocess.run([str(executable)], check=True, capture_output=True)
