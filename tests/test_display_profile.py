from pathlib import Path
import subprocess
import unittest
ROOT=Path(__file__).resolve().parent.parent
class DisplayProfileTests(unittest.TestCase):
    def test_tablet_reference_and_rejects_unrelated_or_malformed_viewports(self):
        p=ROOT/'artifacts/tests/display-profile';p.mkdir(parents=True,exist_ok=True)
        source=p/'test.cpp';source.write_text(r'''
#include "DisplayProfile.h"
#include <cassert>
#include <cmath>
#include <utility>
#include <initializer_list>
int main() {
    DiscoDisplay::Profile p;
    assert(DiscoDisplay::TabletProfile(2752,2064,p));
    assert(std::fabs(p.referenceWidth/p.referenceHeight-4.0f/3.0f)<0.00001f);
    assert(std::fabs(p.referenceHeight*(2752/p.referenceWidth)-2064)<0.01f);
    assert(DiscoDisplay::TabletProfile(1376,1032,p));
    for (auto dimensions : {std::pair<int,int>{2420,1668},{2360,1640},{2266,1488},{2732,2048}}) {
        assert(DiscoDisplay::TabletProfile(dimensions.first,dimensions.second,p));
        assert(std::fabs(p.aspect-float(dimensions.first)/dimensions.second)<0.00001f);
        assert(p.referenceHeight==2048);
        assert(std::fabs(p.referenceWidth/p.referenceHeight-p.aspect)<0.00001f);
    }
    for (auto dimensions : {std::pair<int,int>{0,2064},{-1,2064},{2064,2752},{1920,1080},{16385,12288},{2147483647,1}}) {
        assert(!DiscoDisplay::TabletProfile(dimensions.first,dimensions.second,p));
        assert(p.aspect==0 && p.referenceWidth==0 && p.referenceHeight==0);
    }
}
''')
        exe=p/'test'
        subprocess.run(['xcrun','clang++','-std=c++17','-I',str(ROOT/'runtime/UnityHost'),str(source),'-o',str(exe)],check=True,capture_output=True)
        subprocess.run([str(exe)],check=True,capture_output=True)
