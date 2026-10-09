from pathlib import Path
import struct
import subprocess
import unittest

ROOT = Path(__file__).resolve().parent.parent


class MappedImageTests(unittest.TestCase):
    def test_synthetic_mapping_rebases_and_malformed_packs(self):
        work = ROOT/'artifacts/tests/mapped-image'; work.mkdir(parents=True, exist_ok=True)
        # Entirely synthetic non-executable data; supplied game code is never loaded on Mac.
        file = bytearray(32768); struct.pack_into('<Q', file, 16384, 8)
        pack = (struct.pack('<8s6IQ', b'DSCMAP01', 2, 1, 0, 0, 0, 0, len(file)) +
                struct.pack('<5Q', 0, 16384, 0, 16384, 1) +
                struct.pack('<5Q', 16384, 16384, 16384, 16384, 3) +
                struct.pack('<2Q', 16384, 8) + file)
        (work/'fixture.bin').write_bytes(pack)
        source = work/'test.cpp'
        source.write_text(r'''
#include "MappedImage.h"
#include <fstream>
#include <iterator>
#include <cassert>
bool rejected(std::vector<uint8_t> bytes){try{DiscoMap::Image m(bytes.data(),bytes.size());return false;}catch(const std::runtime_error&){return true;}}
void set64(std::vector<uint8_t>& b,size_t at,uint64_t v){std::memcpy(b.data()+at,&v,8);}
int main(int argc,char** argv){
    assert(argc==2);std::ifstream f(argv[1],std::ios::binary);
    std::vector<uint8_t> bytes((std::istreambuf_iterator<char>(f)),{});
    DiscoMap::Image image(bytes.data(),bytes.size());image.Map();
    uint64_t value;std::memcpy(&value,image.At(16384,8),8);
    assert(value==reinterpret_cast<uint64_t>(image.At(8)));
    image.Seal();assert(image.executableUnchanged);
    for(size_t n: {size_t(0),size_t(39),size_t(119),bytes.size()-1})
        assert(rejected(std::vector<uint8_t>(bytes.begin(),bytes.begin()+n)));
    auto bad=bytes;bad[0]='?';assert(rejected(bad));
    bad=bytes;set64(bad,80,0);assert(rejected(bad)); // Overlapping segments.
    bad=bytes;set64(bad,120,0);assert(rejected(bad)); // Rebase into read-only bytes.
    bad=bytes;set64(bad,128,65536);assert(rejected(bad)); // Target outside image.
    bad=bytes;set64(bad,120,16385);assert(rejected(bad)); // Misaligned slot.
    bad=bytes;set64(bad,136+16384,16);assert(rejected(bad)); // Pointer/plan disagreement.
    bad=bytes;set64(bad,64,65536);assert(rejected(bad)); // File-backed bytes exceed segment.
    bad=bytes;bad.push_back(0);assert(rejected(bad));
}
''')
        exe = work/'test'
        subprocess.run(['xcrun', 'clang++', '-std=c++17', '-I', str(ROOT/'runtime/AndroidHost'),
                        str(source), '-o', str(exe)], check=True, capture_output=True)
        subprocess.run([str(exe), str(work/'fixture.bin')], check=True, capture_output=True)
