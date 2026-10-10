from pathlib import Path
import subprocess
import tempfile
import unittest


class PadTests(unittest.TestCase):
    def test_quick_taps_invalid_axes_and_disconnect(self):
        root=Path(__file__).resolve().parents[1]
        source='''#include "VirtualPadState.h"
#include <cassert>
int main(){DiscoAndroidPad::State state;state.Button(0,true);assert(state.Take().buttons==0);
state.Enable(true);state.Button(1,true);state.Button(1,false);assert(state.Take().buttons==2);assert(state.Take().buttons==0);
state.Axis(0,3,4);auto s=state.Take();assert(std::abs(s.axes[0]-.6f)<.001f&&std::abs(s.axes[1]-.8f)<.001f);
state.Axis(0,NAN,1);assert(state.Take().axes[0]==0&&state.Take().axes[1]==0);
state.Button(100,true);state.Axis(100,1,1);state.Button(0,true);state.Enable(false);s=state.Take();assert(!s.enabled&&!s.buttons&&s.axes[0]==0);
}'''
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder);(path/'test.cpp').write_text(source)
            subprocess.run(['clang++','-std=c++17','-I',str(root/'runtime/AndroidHost'),str(path/'test.cpp'),'-o',str(path/'test')],check=True,capture_output=True)
            subprocess.run([str(path/'test')],check=True,capture_output=True)
