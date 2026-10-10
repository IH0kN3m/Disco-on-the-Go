from pathlib import Path
import subprocess
import tempfile
import unittest


class DialogueTextPolicyTests(unittest.TestCase):
    def test_readability_presets_and_atomic_validation(self):
        root=Path(__file__).resolve().parents[1]
        source=r'''
#include "DialogueTextPolicy.h"
#include <cassert>
#include <climits>
int main() {
    int32_t input[]={16,24,32,40}, output[]={0,0,0,0};
    assert(DiscoDialogue::LargerPresets(input,4,output));
    assert(output[0]==18 && output[1]==27 && output[2]==36 && output[3]==45);
    // The input remains untouched, and all levels retain their relative order.
    assert(input[0]==16 && input[3]==40);
    for (int i=1;i<4;++i) assert(output[i]>output[i-1]);
    int32_t boundary[]={8,9,127,128};
    assert(DiscoDialogue::LargerPresets(boundary,4,output));
    assert(output[0]==9 && output[3]==144);
    int32_t invalid[][4]={{0,24,32,40},{16,24,32,INT_MAX},
        {16,24,24,40},{16,24,23,40},{-1,24,32,40}};
    for (auto& values: invalid) {
        int32_t sentinel[]={1,2,3,4};
        assert(!DiscoDialogue::LargerPresets(values,4,sentinel));
        for(int i=0;i<4;++i) assert(sentinel[i]==i+1);
    }
    assert(!DiscoDialogue::LargerPresets(nullptr,4,output));
    assert(!DiscoDialogue::LargerPresets(input,4,nullptr));
    assert(!DiscoDialogue::LargerPresets(input,3,output));
    assert(!DiscoDialogue::LargerPresets(input,5,output));
}
'''
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);(base/'test.cpp').write_text(source)
            subprocess.run(['xcrun','clang++','-std=c++11','-I',str(root/'runtime/UnityHost'),str(base/'test.cpp'),'-o',str(base/'test')],check=True,capture_output=True)
            subprocess.run([str(base/'test')],check=True,capture_output=True)
