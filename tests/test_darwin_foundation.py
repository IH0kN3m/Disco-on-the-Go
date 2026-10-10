from pathlib import Path
import subprocess
import unittest
ROOT=Path(__file__).resolve().parent.parent
class DarwinFoundationTests(unittest.TestCase):
    def test_timezone_file_bounds_and_object_lifetime(self):
        work=ROOT/'artifacts/tests/darwin-foundation';work.mkdir(parents=True,exist_ok=True)
        source=work/'test.cpp';source.write_text(r'''
#include "DarwinFoundation.h"
#include <cassert>
using namespace DiscoFoundation;
void be(std::vector<uint8_t>& b,size_t at,uint32_t n){for(int i=3;i>=0;--i){b[at+i]=n&255;n>>=8;}}
int main(){
    std::vector<uint8_t> file(120);std::memcpy(file.data(),"tzdata2026c",11);
    be(file,12,24);be(file,16,76);be(file,20,120);std::memcpy(file.data()+24,"Etc/UTC",7);
    be(file,64,0);be(file,68,44);std::memcpy(file.data()+76,"TZif",4);
    auto zones=ParseZones(file);assert(zones.size()==1&&zones[0].name=="Etc/UTC"&&zones[0].bytes.size()==44);
    for(int n=0;n<5;++n){auto bad=file;if(n==0)bad.resize(20);if(n==1)be(bad,16,77);if(n==2)be(bad,64,1);if(n==3)be(bad,68,43);if(n==4)std::memset(bad.data()+24,'x',40);
        bool failed=false;try{ParseZones(bad);}catch(const std::runtime_error&){failed=true;}assert(failed);}
    void* pool=PoolPush();Object* text=Alloc(&stringClass);assert(Message(text,"initWithUTF8String:",reinterpret_cast<uintptr_t>("hello"))==reinterpret_cast<uintptr_t>(text));
    Automatic(text);Retain(text);PoolPop(pool);assert(text->refs==1);
    assert(std::strcmp(reinterpret_cast<const char*>(Message(text,"UTF8String",0)),"hello")==0);Release(text);
}
''')
        exe=work/'test';subprocess.run(['xcrun','clang++','-std=c++17','-I',str(ROOT/'runtime/AndroidHost'),str(source),'-o',str(exe)],check=True,capture_output=True)
        subprocess.run([str(exe)],check=True,capture_output=True,timeout=10)
