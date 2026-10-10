// Original compact-unwind to DWARF frame descriptions for ARM64 call boundaries.
#pragma once
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <vector>
namespace DiscoUnwind {
inline void Uleb(std::vector<uint8_t>& out,uint64_t value){do{uint8_t b=value&127;value>>=7;out.push_back(b|(value?128:0));}while(value);}
template<class T> inline void Put(std::vector<uint8_t>& out,T value){size_t at=out.size();out.resize(at+sizeof(T));std::memcpy(out.data()+at,&value,sizeof(T));}
inline void Finish(std::vector<uint8_t>& out,size_t at){while(out.size()%8)out.push_back(0);uint32_t size=out.size()-at-4;std::memcpy(out.data()+at,&size,4);}
inline void Offset(std::vector<uint8_t>& out,unsigned reg,unsigned units){if(reg<64)out.push_back(0x80|reg);else{out.push_back(5);Uleb(out,reg);}Uleb(out,units);}
inline std::vector<uint8_t> Rules(uint32_t encoding){
    std::vector<uint8_t> rules;unsigned mode=encoding&0x0f000000;
    if(mode==0x04000000){
        if(encoding&0x00fff0e0)throw std::runtime_error("Unknown ARM64 frame encoding flags");
        rules={0x0c,29,16};Offset(rules,29,2);Offset(rules,30,1);unsigned offset=3;
        for(unsigned i=0;i<5;++i)if(encoding&(1u<<i)){Offset(rules,19+2*i,offset++);Offset(rules,20+2*i,offset++);}
        for(unsigned i=0;i<4;++i)if(encoding&(0x100u<<i)){Offset(rules,72+2*i,offset++);Offset(rules,73+2*i,offset++);}
    }else if(mode==0x02000000){
        if(encoding&0xe0)throw std::runtime_error("Unknown frameless encoding flags");
        rules={0x0c,31};Uleb(rules,((encoding>>12)&0xfff)*16);
        rules.push_back(0x08);Uleb(rules,30); // return address remains in LR
        unsigned offset=1;
        for(unsigned i=0;i<5;++i)if(encoding&(1u<<i)){Offset(rules,19+2*i,offset++);Offset(rules,20+2*i,offset++);}
        for(unsigned i=0;i<4;++i)if(encoding&(0x100u<<i)){Offset(rules,72+2*i,offset++);Offset(rules,73+2*i,offset++);}
        if((offset-1)*8>((encoding>>12)&0xfff)*16)throw std::runtime_error("Saved registers exceed frameless stack");
    }else throw std::runtime_error("Encoding requires original DWARF or has no unwind information");
    return rules;
}
inline size_t Cie(std::vector<uint8_t>& out,uintptr_t personality){
    size_t at=out.size();Put<uint32_t>(out,0);Put<uint32_t>(out,0);
    const uint8_t prefix[]={1,'z','P','L','R',0,1,0x78,30,11,0};for(uint8_t b:prefix)out.push_back(b);
    Put<uint64_t>(out,personality);out.push_back(0);out.push_back(0);Finish(out,at);return at;
}
inline size_t Fde(std::vector<uint8_t>& out,size_t cie,uintptr_t begin,size_t bytes,uintptr_t lsda,uint32_t encoding){
    auto rules=Rules(encoding);size_t at=out.size();
    if(cie>=at||at-cie>UINT32_MAX-4||!bytes)throw std::runtime_error("Invalid DWARF frame ownership");
    Put<uint32_t>(out,0);Put<uint32_t>(out,uint32_t(at+4-cie));Put<uint64_t>(out,begin);Put<uint64_t>(out,bytes);
    Uleb(out,8);Put<uint64_t>(out,lsda);out.insert(out.end(),rules.begin(),rules.end());Finish(out,at);return at;
}
}
