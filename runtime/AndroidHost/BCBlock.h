// Original bounded reference decoder for BC1 RGBA/BC3 LDR blocks.
// BC3 always uses four RGB colors, independent of endpoint order (S3TC spec).
#pragma once
#include <cstddef>
#include <cstdint>
namespace DiscoBC {
inline uint32_t Color565(uint32_t v) {
    uint32_t r=v>>11, g=(v>>5)&63, b=v&31;
    return (r<<3 | r>>2) | ((g<<2 | g>>4)<<8) | ((b<<3 | b>>2)<<16) | 0xff000000u;
}
inline uint32_t Mix(uint32_t a,uint32_t b,unsigned aw,unsigned bw,unsigned divisor) {
    uint32_t result=0xff000000u;
    for(unsigned shift=0;shift<24;shift+=8)
        result|=((aw*((a>>shift)&255)+bw*((b>>shift)&255))/divisor)<<shift;
    return result;
}
inline bool Decode(const uint8_t* data,size_t size,bool bc3,uint32_t* output,size_t pixels) {
    if(!data || !output || size!=(bc3?16u:8u) || pixels!=16) return false;
    const uint8_t* color=data+(bc3?8:0);
    uint32_t a=color[0] | uint32_t(color[1])<<8, b=color[2] | uint32_t(color[3])<<8;
    uint32_t palette[4]={Color565(a),Color565(b),0,0};
    if(bc3 || a>b) {palette[2]=Mix(palette[0],palette[1],2,1,3);palette[3]=Mix(palette[0],palette[1],1,2,3);}
    else palette[2]=Mix(palette[0],palette[1],1,1,2);
    uint32_t selectors=uint32_t(color[4]) | uint32_t(color[5])<<8 | uint32_t(color[6])<<16 | uint32_t(color[7])<<24;
    uint64_t alphaBits=0;
    if(bc3) for(unsigned i=0;i<6;++i) alphaBits|=uint64_t(data[i+2])<<(i*8);
    for(unsigned i=0;i<16;++i) {
        output[i]=palette[(selectors>>(2*i))&3];
        if(!bc3) continue;
        unsigned index=(alphaBits>>(3*i))&7, value;
        if(index<2)value=data[index];
        else if(data[0]>data[1])value=((8-index)*data[0]+(index-1)*data[1])/7;
        else if(index<6)value=((6-index)*data[0]+(index-1)*data[1])/5;
        else value=index==6?0:255;
        output[i]=(output[i]&0xffffffu)|(value<<24);
    }
    return true;
}
}
