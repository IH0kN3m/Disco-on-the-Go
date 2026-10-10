from pathlib import Path
import subprocess
import unittest
ROOT = Path(__file__).resolve().parent.parent
class GraphicsFormatPolicyTests(unittest.TestCase):
    def test_readback_bounds_prevent_overflow(self):
        folder = ROOT / 'artifacts/tests/readback-policy'; folder.mkdir(parents=True, exist_ok=True)
        source = folder / 'test.cpp'
        source.write_text('''
#include "ReadbackPolicy.h"
#include <cassert>
#include <utility>
#include <initializer_list>
int main() {
    size_t bytes=123;
    assert(DiscoReadbackPolicy::Shape(2,2,bytes)&&bytes==16);
    assert(DiscoReadbackPolicy::Shape(4096,4096,bytes)&&bytes==67108864);
    for(auto shape: {std::pair<int,int>{0,1},{1,0},{-1,2},{1,-1},{4097,1},{1,4097},{2147483647,2147483647}}){
        assert(!DiscoReadbackPolicy::Shape(shape.first,shape.second,bytes)&&bytes==0);
    }
}
''')
        executable = folder / 'test'
        subprocess.run(['xcrun', 'clang++', '-std=c++17', '-I', str(ROOT/'runtime/AndroidHost'), str(source), '-o', str(executable)], check=True, capture_output=True)
        subprocess.run([str(executable)], check=True, capture_output=True)

    def test_promotion_requires_unsupported_source_and_supported_destination(self):
        folder = ROOT / 'artifacts/tests/graphics-format'; folder.mkdir(parents=True, exist_ok=True)
        source = folder / 'test.cpp'
        source.write_text('''
#include "GraphicsFormatPolicy.h"
#include <cassert>
#include <initializer_list>
int main() {
    using namespace DiscoGraphicsFormat;
    auto unsupported=[](int,int){return false;};
    auto all=[](int,int){return true;};
    auto floats=[](int f,int usage){assert(usage==4);return f==49||f==50;};
    assert(Compatible(21,floats)==49);
    assert(Compatible(22,floats)==50);
    assert(Compatible(21,unsupported)==21);
    assert(Compatible(22,unsupported)==22);
    assert(Compatible(21,all)==21);
    assert(Compatible(22,all)==22);
    for(int value: {0,5,13,49,50,-1,1000}) assert(Compatible(value,floats)==value);
}
''')
        executable = folder / 'test'
        subprocess.run(['xcrun', 'clang++', '-std=c++17', '-I', str(ROOT/'runtime/UnityHost'), str(source), '-o', str(executable)], check=True, capture_output=True)
        subprocess.run([str(executable)], check=True, capture_output=True)
