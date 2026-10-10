from pathlib import Path
import subprocess
import unittest
ROOT = Path(__file__).resolve().parent.parent

class DarwinLocaleTests(unittest.TestCase):
    def test_borrowed_handles_encodings_and_bounds(self):
        work=ROOT/'artifacts/tests/darwin-locale';work.mkdir(parents=True,exist_ok=True)
        source=work/'test.cpp';source.write_text(r'''
#include "DarwinLocale.h"
#include <cassert>
using namespace DiscoLocale;
int main(){
    SetTag("zh-Hant-TW");auto* locale=CopyCurrent();
    assert(Identifier(locale)->text=="zh_Hant_TW");
    assert(Value(locale,&languageKey)->text=="zh");
    assert(Value(locale,&scriptKey)->text=="Hant");
    assert(Value(locale,&countryKey)->text=="TW");
    Release(Value(locale,&languageKey)); // borrowed handle remains live
    char buffer[3]={};assert(CString(Value(locale,&languageKey),buffer,3,0));
    assert(std::strcmp(buffer,"zh")==0);
    assert(!CString(Value(locale,&languageKey),buffer,2,0x08000100));
    intptr_t used=-1;assert(Bytes(Identifier(locale),{0,10},0,0,false,nullptr,0,&used)==10&&used==10);
    uint8_t bytes[4]={};assert(Bytes(Identifier(locale),{3,4},0x600,0,false,bytes,3,&used)==3&&used==3);
    assert(std::memcmp(bytes,"Han",3)==0);Release(locale);
    SetTag("en");locale=CopyCurrent();assert(Value(locale,&countryKey)==nullptr&&Value(locale,&scriptKey)==nullptr);Release(locale);
    assert(MaxSize(-1,0)==-1&&MaxSize(INTPTR_MAX,0x08000100)==-1);
}
''')
        exe=work/'test';subprocess.run(['xcrun','clang++','-std=c++17','-I',str(ROOT/'runtime/AndroidHost'),str(source),'-o',str(exe)],check=True,capture_output=True)
        subprocess.run([str(exe)],check=True,capture_output=True,timeout=10)
