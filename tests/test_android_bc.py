from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parent.parent


class AndroidBCDecodeTests(unittest.TestCase):
    def test_known_colors_alpha_modes_and_rejected_buffers(self):
        work = ROOT / 'artifacts/tests/android-bc'
        work.mkdir(parents=True, exist_ok=True)
        source = work / 'test.cpp'
        source.write_text(r'''
#include "BCBlock.h"
#include <cassert>
#include <cstring>
int main() {
    // Red/green endpoints, selectors 0,1,2,3 repeated across all rows.
    uint8_t color[8]={0,248,224,7,228,228,228,228};
    uint32_t pixels[18];
    for(auto &v:pixels)v=0x12345678;
    assert(DiscoBC::Decode(color,8,false,pixels+1,16));
    const uint32_t expected[]={0xff0000ff,0xff00ff00,0xff0055aa,0xff00aa55};
    for(int i=0;i<16;++i)assert(pixels[i+1]==expected[i%4]);
    assert(pixels[0]==0x12345678 && pixels[17]==0x12345678);
    // Reversed endpoints select BC1's midpoint and transparent black.
    uint8_t reversed[8]={224,7,0,248,228,228,228,228};
    assert(DiscoBC::Decode(reversed,8,false,pixels+1,16));
    const uint32_t transparent[]={0xff00ff00,0xff0000ff,0xff007f7f,0};
    for(int i=0;i<16;++i)assert(pixels[i+1]==transparent[i%4]);
    uint8_t bc3[16]={};
    std::memcpy(bc3+8,reversed,8);
    // Select every alpha entry twice, including selectors crossing byte/word boundaries.
    uint64_t selectors=0;
    for(int i=0;i<16;++i)selectors|=uint64_t(i%8)<<(3*i);
    for(int i=0;i<6;++i)bc3[i+2]=selectors>>(8*i);
    const uint8_t alpha[3][8]={{255,0,218,182,145,109,72,36},
                             {0,255,51,102,153,204,0,255},
                             {42,42,42,42,42,42,0,255}};
    const uint32_t opaque[]={0x00ff00,0x0000ff,0x00aa55,0x0055aa};
    for(int mode=0;mode<3;++mode) {
        bc3[0]=alpha[mode][0];bc3[1]=alpha[mode][1];
        assert(DiscoBC::Decode(bc3,16,true,pixels+1,16));
        for(int i=0;i<16;++i)
            assert(pixels[i+1]==(opaque[i%4]|uint32_t(alpha[mode][i%8])<<24));
    }
    // Malformed inputs are rejected without touching any output.
    for(auto &v:pixels)v=0x12345678;
    assert(!DiscoBC::Decode(nullptr,8,false,pixels+1,16));
    assert(!DiscoBC::Decode(color,8,false,nullptr,16));
    for(unsigned size=0;size<18;++size) {
        if(size!=8)assert(!DiscoBC::Decode(color,size,false,pixels+1,16));
        if(size!=16)assert(!DiscoBC::Decode(bc3,size,true,pixels+1,16));
    }
    assert(!DiscoBC::Decode(color,8,false,pixels+1,15));
    assert(!DiscoBC::Decode(bc3,16,true,pixels+1,17));
    for(auto v:pixels)assert(v==0x12345678);
}
''')
        executable = work / 'test'
        subprocess.run(['xcrun', 'clang++', '-std=c++17', '-I', str(ROOT / 'runtime/AndroidHost'),
                        str(source), '-o', str(executable)], check=True, capture_output=True)
        subprocess.run([str(executable)], check=True, capture_output=True)
