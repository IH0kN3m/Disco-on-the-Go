#pragma once
#include <array>
#include <cmath>
#include <cstdint>
namespace DiscoAndroidPad {
struct Snapshot {bool enabled=false;uint32_t buttons=0;std::array<float,4> axes{};};
class State {
    Snapshot value;
    uint32_t pressed=0;
public:
    void Enable(bool enabled){value={};value.enabled=enabled;pressed=0;}
    void Button(unsigned button,bool down){
        if(!value.enabled||button>=13)return;
        uint32_t bit=1u<<button;
        if(down){if(!(value.buttons&bit))pressed|=bit;value.buttons|=bit;}
        else value.buttons&=~bit;
    }
    void Axis(unsigned stick,float x,float y){
        if(!value.enabled||stick>=2)return;
        if(!std::isfinite(x)||!std::isfinite(y)){x=y=0;}
        float length=std::hypot(x,y);if(length>1){x/=length;y/=length;}
        value.axes[stick*2]=x;value.axes[stick*2+1]=y;
    }
    Snapshot Take(){auto result=value;result.buttons|=pressed;pressed=0;return result;}
};
}
