from pathlib import Path
import subprocess
import unittest
ROOT=Path(__file__).resolve().parent.parent
class DarwinDirectoryTests(unittest.TestCase):
    def test_layout_name_limits_and_ownership(self):
        work=ROOT/'artifacts/tests/darwin-directory';work.mkdir(parents=True,exist_ok=True)
        source=work/'test.cpp';source.write_text(r'''
#include "DarwinDirectory.h"
#include <cassert>
#include <cstddef>
#include <string>
int main(){
    using namespace DiscoDirectory;Entry e{};
    static_assert(offsetof(Entry,name)==21);static_assert(offsetof(Entry,nameLength)==18);
    assert(Convert(e,100,500,8,"save.dat"));assert(e.inode==100&&e.offset==500&&e.nameLength==8&&e.recordLength==32);
    assert(std::strcmp(e.name,"save.dat")==0);
    std::string limit(1023,'x');assert(Convert(e,1,2,4,limit.c_str()));assert(e.name[1023]==0);
    limit+='x';assert(!Convert(e,1,2,4,limit.c_str()));assert(!Convert(e,1,2,4,nullptr));
}
''')
        exe=work/'test';subprocess.run(['xcrun','clang++','-std=c++17','-I',str(ROOT/'runtime/AndroidHost'),str(source),'-o',str(exe)],check=True,capture_output=True)
        subprocess.run([str(exe)],check=True,capture_output=True,timeout=10)
