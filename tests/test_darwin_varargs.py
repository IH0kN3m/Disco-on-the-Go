from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parent.parent


class DarwinVarargsTests(unittest.TestCase):
    def test_stack_slots_truncation_and_rejected_formats(self):
        work = ROOT / 'artifacts/tests/darwin-varargs'
        work.mkdir(parents=True, exist_ok=True)
        source = work / 'test.cpp'
        source.write_text(r'''
#include <cassert>
#include <cstdint>
#include <cstring>
#include <cstdio>
extern "C" int DiscoSnprintf(char*,size_t,const char*,const uint8_t*);
int main(int argc,char** argv){
    uint64_t args[16]{};char out[128]{};
    if(argc>1){DiscoSnprintf(out,sizeof(out),argv[1],reinterpret_cast<uint8_t*>(args));return 0;}
    args[0]=uint64_t(-12);args[1]=0x123456789ULL;args[2]=reinterpret_cast<uint64_t>("sample");
    double d=1.25;std::memcpy(&args[3],&d,8);
    int n=DiscoSnprintf(out,sizeof(out),"%d %llx %s %.2Lf %%",reinterpret_cast<uint8_t*>(args));
    assert(!std::strcmp(out,"-12 123456789 sample 1.25 %")&&n==int(std::strlen(out)));
    char small[5]={'x','x','x','x','Q'};int wanted=DiscoSnprintf(small,4,"%d %llx",reinterpret_cast<uint8_t*>(args));
    assert(wanted==13&&!std::strcmp(small,"-12")&&small[4]=='Q');
    assert(DiscoSnprintf(nullptr,0,"hello",nullptr)==5);
    args[0]=uint64_t(-6);args[1]=2;std::memcpy(&args[2],&d,8);
    assert(DiscoSnprintf(out,sizeof(out),"%*.*f",reinterpret_cast<uint8_t*>(args))==6&&!std::strcmp(out,"1.25  "));
}
''')
        exe = work / 'test'
        subprocess.run(['xcrun', 'clang++', '-std=c++17', str(source),
                        str(ROOT / 'runtime/AndroidHost/DarwinVarargs.cpp'), '-o', str(exe)],
                       check=True, capture_output=True)
        subprocess.run([str(exe)], check=True, capture_output=True, timeout=10)
        for malformed in ('%', '%n', '%ls', '%1$d', '%99999999d'):
            result = subprocess.run([str(exe), malformed], capture_output=True, timeout=10)
            self.assertNotEqual(result.returncode, 0, malformed)
            self.assertIn(b'Darwin format unsupported', result.stderr)
