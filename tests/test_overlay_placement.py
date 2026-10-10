from pathlib import Path
import subprocess
import tempfile
import unittest


class OverlayPlacementTests(unittest.TestCase):
    def test_safe_area_rotation_persistence_and_invalid_geometry(self):
        root=Path(__file__).resolve().parents[1]
        code=r'''
#include "OverlayPlacement.h"
#include <cassert>
int main(){
    using namespace DiscoOverlay;Area a,b;
    assert(Bounds(1376,1032,8,24,8,28,42,38,a));
    Point edge=Clamp(a,{-100,9000});
    assert(edge.x==29&&edge.y==985);
    Point anchor=Normalize(a,edge);assert(anchor.x==0&&anchor.y==1);
    assert(Bounds(1032,1376,24,8,28,8,42,38,b));
    Point rotated=Restore(b,anchor);assert(rotated.x==45&&rotated.y==1349);
    Point middle=Restore(b,{.3,.7});Point roundTrip=Normalize(b,middle);
    assert(std::abs(roundTrip.x-.3)<1e-9&&std::abs(roundTrip.y-.7)<1e-9);
    assert(Restore(a,{NAN,INFINITY}).x==a.x+a.width);
    assert(Restore(a,{-5,4}).x==a.x&&Restore(a,{-5,4}).y==a.y+a.height);
    assert(Bounds(42,38,0,0,0,0,42,38,b));
    assert(Normalize(b,{1000,1000}).x==0&&Normalize(b,{1000,1000}).y==0);
    assert(!Bounds(40,38,0,0,0,0,42,38,b));
    assert(!Bounds(NAN,38,0,0,0,0,42,38,b));
    assert(!Bounds(1376,1032,-1,0,0,0,42,38,b));
    assert(!Bounds(1376,1032,0,0,0,0,0,38,b));
}
'''
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);source=base/'test.cpp';source.write_text(code)
            subprocess.run(['xcrun','clang++','-std=c++11','-I',str(root/'runtime/UnityHost'),str(source),'-o',str(base/'test')],check=True,capture_output=True)
            subprocess.run([str(base/'test')],check=True,capture_output=True)
