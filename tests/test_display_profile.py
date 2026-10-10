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
    assert(DiscoDisplay::NativeAspectMode(p)==3);
    assert(std::fabs(p.referenceWidth/p.referenceHeight-4.0f/3.0f)<0.00001f);
    assert(std::fabs(p.referenceHeight*(2752/p.referenceWidth)-2064)<0.01f);
    // New dialogue canvases can appear without any scene/view-size change.
    DiscoDisplay::LayoutOwners before={100,200,1};
    assert(DiscoDisplay::SameOwners(before,{100,200,1}));
    assert(!DiscoDisplay::SameOwners(before,{100,200,2}));
    assert(!DiscoDisplay::SameOwners(before,{101,200,1}));
    assert(!DiscoDisplay::SameOwners(before,{100,201,1}));
    assert(DiscoDisplay::MatchingReference(p.referenceWidth,p.referenceHeight,p));
    assert(!DiscoDisplay::MatchingReference(2372,2048,p));
    assert(!DiscoDisplay::MatchingReference(NAN,2048,p));
    assert(DiscoDisplay::TabletProfile(1376,1032,p));
    for (auto dimensions : {std::pair<int,int>{2420,1668},{2360,1640},{2266,1488},{2732,2048}}) {
        assert(DiscoDisplay::TabletProfile(dimensions.first,dimensions.second,p));
        assert(std::fabs(p.aspect-float(dimensions.first)/dimensions.second)<0.00001f);
        assert(p.referenceHeight==2048);
        assert(std::fabs(p.referenceWidth/p.referenceHeight-p.aspect)<0.00001f);
    }
    for (auto dimensions : {std::pair<int,int>{2960,1848},{1920,1080}}) {
        assert(DiscoDisplay::TabletProfile(dimensions.first,dimensions.second,p));
        assert(std::abs(p.referenceWidth/p.referenceHeight-float(dimensions.first)/dimensions.second)<0.00001f);
        assert(DiscoDisplay::NativeAspectMode(p)==(dimensions.first==2960 ? 2 : 0));
    }
    assert(DiscoDisplay::NativeAspectMode({1.45f,0,0})==3);
    for (auto dimensions : {std::pair<int,int>{0,2064},{-1,2064},{2064,2752},{3440,1440},{16385,12288},{2147483647,1}}) {
        assert(!DiscoDisplay::TabletProfile(dimensions.first,dimensions.second,p));
        assert(p.aspect==0 && p.referenceWidth==0 && p.referenceHeight==0);
    }
}
''')
        exe=p/'test'
        subprocess.run(['xcrun','clang++','-std=c++17','-I',str(ROOT/'runtime/UnityHost'),str(source),'-o',str(exe)],check=True,capture_output=True)
        subprocess.run([str(exe)],check=True,capture_output=True)
