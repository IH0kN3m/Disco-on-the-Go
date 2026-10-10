from pathlib import Path
import subprocess
import unittest
ROOT=Path(__file__).resolve().parent.parent

class DwarfFramesTests(unittest.TestCase):
    def test_cfa_saved_registers_and_invalid_encodings(self):
        work=ROOT/'artifacts/tests/dwarf-frames';work.mkdir(parents=True,exist_ok=True)
        source=work/'test.cpp';source.write_text(r'''
#include "DwarfFrames.h"
#include <cassert>
using namespace DiscoUnwind;
int main(){
    // stp x20,x19,[sp,#-32]!; stp fp,lr,[sp,#16]; add fp,sp,#16.
    auto r=Rules(0x04000001);
    const uint8_t expected[]={12,29,16,0x9d,2,0x9e,1,0x93,3,0x94,4};
    assert(r==std::vector<uint8_t>(expected,expected+sizeof(expected)));
    auto leaf=Rules(0x02003000);const uint8_t expectedLeaf[]={12,31,48,8,30};
    assert(leaf==std::vector<uint8_t>(expectedLeaf,expectedLeaf+sizeof(expectedLeaf)));
    std::vector<uint8_t> bytes;auto cie=Cie(bytes,0x1234567812345678ULL);auto fde=Fde(bytes,cie,0x1000,0x80,0x9000,0x04000001);
    uint32_t back;std::memcpy(&back,bytes.data()+fde+4,4);assert(fde+4-back==cie);
    uint64_t pc;std::memcpy(&pc,bytes.data()+fde+8,8);assert(pc==0x1000);
    for(auto e:{0u,0x05000000u,0x04000020u,0x02000001u}){bool bad=false;try{Rules(e);}catch(const std::runtime_error&){bad=true;}assert(bad);}
    bool bad=false;try{Fde(bytes,bytes.size(),0,1,0,0x04000000);}catch(const std::runtime_error&){bad=true;}assert(bad);
}
''')
        exe=work/'test';subprocess.run(['xcrun','clang++','-std=c++17','-I',str(ROOT/'runtime/AndroidHost'),str(source),'-o',str(exe)],check=True,capture_output=True)
        subprocess.run([str(exe)],check=True,capture_output=True,timeout=10)
