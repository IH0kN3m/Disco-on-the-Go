// Bounded UI-thread to Unity-thread gesture delivery; no game dependencies.
#pragma once
#include <array>
#include <cstddef>
#include <cmath>
namespace DiscoAndroidTouch {
struct Event { int phase, first, second; double scale; float x1=0,y1=0,x2=0,y2=0; };
class Queue {
    std::array<Event,32> values{};
    size_t count=0;
public:
    void Push(Event event) {
        bool positions=true;
        for(float value:{event.x1,event.y1,event.x2,event.y2})positions=positions&&std::isfinite(value)&&value>=0&&value<=1;
        if(event.phase<0||event.phase>2||!std::isfinite(event.scale)||event.scale<0.0001||event.scale>10000||
           (event.phase&&(!positions||event.first<0||event.second<0||event.first==event.second))) {
            count=1;values[0]={0,0,0,1};return;
        }
        if(event.phase==2&&count&&values[count-1].phase==2&&values[count-1].first==event.first&&values[count-1].second==event.second){
            values[count-1]=event;return;
        }
        if(count==values.size()) {
            count=1;values[0]={0,0,0,1};
            if(event.phase!=1)return;
        }
        values[count++]=event;
    }
    size_t Drain(std::array<Event,32>& output) { output=values;size_t result=count;count=0;return result; }
};
}
