from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parent.parent


class AndroidTouchQueueTests(unittest.TestCase):
    def test_gesture_order_coalescing_overflow_and_invalid_input_cancel(self):
        directory = ROOT / 'artifacts/tests/android-touch'
        directory.mkdir(parents=True, exist_ok=True)
        source = directory / 'test.cpp'
        source.write_text(r'''
#include "TouchQueue.h"
#include <cassert>
#include <limits>
int main() {
    using namespace DiscoAndroidTouch;
    Queue q;std::array<Event,32> events;
    assert(q.Drain(events)==0);
    q.Push({1,3,4,1});
    for(int i=0;i<100;++i)q.Push({2,3,4,1+i*.01});
    q.Push({0,0,0,1});
    assert(q.Drain(events)==3);
    assert(events[0].phase==1&&events[0].first==3);
    assert(events[1].phase==2&&events[1].scale==1.99);
    assert(events[2].phase==0);
    assert(q.Drain(events)==0);
    q.Push({1,0,1,1});q.Push({2,0,1,2});q.Push({2,0,2,3});
    assert(q.Drain(events)==3); // A new finger pair cannot replace another pair's event.
    for(int i=0;i<20;++i){q.Push({1,0,1,1});q.Push({0,0,0,1});}
    assert(q.Drain(events)<=32&&events[0].phase==0); // Overflow releases the camera.
    for(double bad:{0.,-1.,10001.,std::numeric_limits<double>::infinity(),std::numeric_limits<double>::quiet_NaN()}){
        q.Push({1,0,1,1});q.Push({2,0,1,bad});
        assert(q.Drain(events)==1&&events[0].phase==0);
    }
    q.Push({9,0,1,1});assert(q.Drain(events)==1&&events[0].phase==0);
    q.Push({1,-1,1,1});assert(q.Drain(events)==1&&events[0].phase==0);
    q.Push({1,1,1,1});assert(q.Drain(events)==1&&events[0].phase==0);
    q.Push({1,0,1,1,-.1f,0,1,1});assert(q.Drain(events)==1&&events[0].phase==0);
    q.Push({1,0,1,1,0,0,1,1});assert(q.Drain(events)==1&&events[0].phase==1);
}
''')
        executable = directory / 'test'
        subprocess.run(['xcrun', 'clang++', '-std=c++17', '-I', str(ROOT / 'runtime/AndroidHost'),
                        str(source), '-o', str(executable)], check=True, capture_output=True)
        subprocess.run([str(executable)], check=True, capture_output=True)
