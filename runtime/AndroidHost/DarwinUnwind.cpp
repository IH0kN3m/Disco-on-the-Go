#include "RuntimeLoader.h"
#include "DwarfFrames.h"
#include <android/log.h>
#include <memory>
#include <tuple>
extern "C" void __register_frame(const void*);
namespace DiscoRuntime {
void RegisterUnwind(AAssetManager* manager,DiscoMap::Image& image,const char* name){
    std::unique_ptr<AAsset,decltype(&AAsset_close)> asset(AAssetManager_open(manager,name,AASSET_MODE_BUFFER),AAsset_close);
    DiscoMap::Require(bool(asset),"Unwind package missing");
    size_t length=AAsset_getLength64(asset.get());auto* data=static_cast<const uint8_t*>(AAsset_getBuffer(asset.get()));
    DiscoMap::Require(data&&length>=16&&!std::memcmp(data,"DSCUW001",8),"Invalid unwind package");
    uint32_t count,eh;std::memcpy(&count,data+8,4);std::memcpy(&eh,data+12,4);
    DiscoMap::Require(count>0&&count<=250000&&length==16+size_t(count)*20,"Invalid unwind record count");
    auto* frames=new std::vector<uint8_t>();frames->reserve(size_t(count)*96+64);
    std::vector<size_t> offsets;std::vector<const void*> original;
    uintptr_t personality=0;size_t cie=0;unsigned skipped=0;
    for(unsigned i=0;i<count;++i){uint32_t v[5];std::memcpy(v,data+16+20*i,20);
        auto [begin,end,encoding,lsda,slot]=std::tuple{v[0],v[1],v[2],v[3],v[4]};
        DiscoMap::Require(end>begin,"Invalid unwind interval");image.At(begin,end-begin,4);
        unsigned mode=encoding&0x0f000000;
        if(mode==0x03000000){original.push_back(image.At(uint64_t(eh)+(encoding&0xffffff),8));continue;}
        if(mode==0){DiscoMap::Require(!encoding&&!lsda&&!slot,"Invalid empty unwind record");++skipped;continue;}
        if(slot){uintptr_t resolved;std::memcpy(&resolved,image.At(slot,8),8);if(personality)DiscoMap::Require(personality==resolved,"Multiple unwind personalities unsupported");else personality=resolved;}
    }
    DiscoMap::Require(personality,"No unwind personality found");cie=DiscoUnwind::Cie(*frames,personality);
    for(unsigned i=0;i<count;++i){uint32_t v[5];std::memcpy(v,data+16+20*i,20);unsigned mode=v[2]&0x0f000000;
        if(mode!=0x02000000&&mode!=0x04000000)continue;
        offsets.push_back(DiscoUnwind::Fde(*frames,cie,reinterpret_cast<uintptr_t>(image.At(v[0])),v[1]-v[0],v[3]?reinterpret_cast<uintptr_t>(image.At(v[3])):0,v[2]));
    }
    for(size_t offset:offsets)__register_frame(frames->data()+offset);
    for(const void* fde:original)__register_frame(fde);
    __android_log_print(ANDROID_LOG_INFO,"DiscoRuntime","Unwind registered: %zu translated frames, %zu original DWARF, %u unavailable",offsets.size(),original.size(),skipped);
}
}
