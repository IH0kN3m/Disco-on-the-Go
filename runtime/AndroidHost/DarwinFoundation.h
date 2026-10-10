// Narrow Objective-C ABI adapter for IL2CPP's NSString/NSTimeZone queries.
// Timezone payloads come from Android's installed tzdata, not bundled copies.
#pragma once
#include <algorithm>
#include <atomic>
#include <cstdio>
#include <cstring>
#include <memory>
#include <mutex>
#include <string>
#include <vector>
#include <stdexcept>
#include <cstdint>
namespace DiscoFoundation {
struct Zone {std::string name;std::vector<uint8_t> bytes;};
inline uint32_t Big(const uint8_t* p){return (uint32_t(p[0])<<24)|(uint32_t(p[1])<<16)|(uint32_t(p[2])<<8)|p[3];}
inline std::vector<Zone> ParseZones(const std::vector<uint8_t>& bytes){
    if(bytes.size()<24||std::memcmp(bytes.data(),"tzdata",6)||bytes[11])throw std::runtime_error("Invalid Android tzdata header");
    uint32_t index=Big(bytes.data()+12),data=Big(bytes.data()+16),end=Big(bytes.data()+20);
    if(index!=24||data<index||(data-index)%52||data>bytes.size()||end<data||end>bytes.size()||(data-index)/52>4096)throw std::runtime_error("Invalid timezone index ownership");
    std::vector<Zone> zones;
    for(size_t at=index;at<data;at+=52){const uint8_t* row=bytes.data()+at;const auto* zero=static_cast<const uint8_t*>(std::memchr(row,0,40));
        if(!zero||zero==row)throw std::runtime_error("Invalid timezone name");std::string name(reinterpret_cast<const char*>(row),zero-row);
        uint32_t offset=Big(row+40),size=Big(row+44);
        if(size<44||offset>end-data||size>end-data-offset||std::memcmp(bytes.data()+data+offset,"TZif",4))throw std::runtime_error("Timezone payload escapes data");
        if(!zones.empty()&&zones.back().name>=name)throw std::runtime_error("Timezone names unordered/duplicated");
        zones.push_back({name,{bytes.begin()+data+offset,bytes.begin()+data+offset+size}});
    }
    return zones;
}
inline const std::vector<Zone>& Zones(){
    static const auto zones=[](){
        const char* paths[]={"/apex/com.android.tzdata/etc/tz/tzdata","/system/usr/share/zoneinfo/tzdata"};
        for(auto* path:paths){std::unique_ptr<FILE,decltype(&std::fclose)> file(std::fopen(path,"rb"),std::fclose);if(!file)continue;
            if(std::fseek(file.get(),0,SEEK_END))throw std::runtime_error("Timezone file seek failed");long size=std::ftell(file.get());
            if(size<24||size>16*1024*1024)throw std::runtime_error("Timezone file size invalid");std::rewind(file.get());std::vector<uint8_t> bytes(size);
            if(std::fread(bytes.data(),1,size,file.get())!=size)throw std::runtime_error("Timezone file truncated");return ParseZones(bytes);
        }
        throw std::runtime_error("Android timezone database unavailable");
    }();return zones;
}
enum class Kind {String,TimeZone,Data,Array,StringClass,TimeZoneClass};
struct Object {Kind kind;std::atomic<unsigned> refs{1};bool immortal=false;std::string text;std::vector<uint8_t> bytes;std::vector<Object*> children;
    explicit Object(Kind k,bool permanent=false):kind(k),immortal(permanent){}
    ~Object();
};
inline void Release(Object* object){if(object&&!object->immortal&&object->refs.fetch_sub(1)==1)delete object;}
inline Object::~Object(){for(auto* child:children)Release(child);}
inline Object* Retain(Object* object){if(object&&!object->immortal)++object->refs;return object;}
inline Object stringClass{Kind::StringClass,true},zoneClass{Kind::TimeZoneClass,true};
inline std::mutex zoneLock;inline std::string defaultZone="Etc/UTC";
inline void SetZone(const char* name){if(!name||std::strlen(name)>128)throw std::runtime_error("Invalid default timezone");std::lock_guard<std::mutex> lock(zoneLock);defaultZone=name;}
inline thread_local std::vector<std::vector<Object*>*> pools;
inline void* PoolPush(){auto* pool=new std::vector<Object*>();pools.push_back(pool);return pool;}
inline void PoolPop(void* value){if(pools.empty()||pools.back()!=value)std::abort();auto* pool=pools.back();pools.pop_back();for(auto* object:*pool)Release(object);delete pool;}
inline Object* Automatic(Object* object){if(!pools.empty())pools.back()->push_back(object);return object;}
inline Object* RetainAutorelease(Object* object){return Automatic(Retain(object));}
inline Object* String(const std::string& text){auto* result=new Object(Kind::String);result->text=text;return result;}
inline Object* Alloc(Object* type){if(type==&stringClass)return new Object(Kind::String);if(type==&zoneClass)return new Object(Kind::TimeZone);std::abort();}
inline Object* InitializeZone(Object* object,const std::string& name){
    const auto& zones=Zones();auto it=std::lower_bound(zones.begin(),zones.end(),name,[](const Zone& zone,const std::string& value){return zone.name<value;});
    if(it==zones.end()||it->name!=name){Release(object);return nullptr;}
    object->text=name;auto* data=new Object(Kind::Data);data->bytes=it->bytes;object->children={String(name),data};return object;
}
inline uintptr_t Message(Object* object,const char* selector,uintptr_t argument){
    if(!object)return 0;if(!selector)std::abort();
    if(object==&zoneClass&&!std::strcmp(selector,"localTimeZone")){std::lock_guard<std::mutex> lock(zoneLock);auto* result=InitializeZone(new Object(Kind::TimeZone),defaultZone);return reinterpret_cast<uintptr_t>(result?Automatic(result):nullptr);}
    if(object==&zoneClass&&!std::strcmp(selector,"knownTimeZoneNames")){static Object* names=[](){auto* result=new Object(Kind::Array,true);for(const auto& zone:Zones())result->children.push_back(String(zone.name));return result;}();return reinterpret_cast<uintptr_t>(names);}
    if(object->kind==Kind::String){
        if(!std::strcmp(selector,"initWithUTF8String:")){const char* text=reinterpret_cast<const char*>(argument);if(!text)std::abort();object->text=text;return reinterpret_cast<uintptr_t>(object);}
        if(!std::strcmp(selector,"UTF8String"))return reinterpret_cast<uintptr_t>(object->text.c_str());
    }
    if(object->kind==Kind::TimeZone){
        if(!std::strcmp(selector,"initWithName:")){auto* name=reinterpret_cast<Object*>(argument);if(!name||name->kind!=Kind::String)std::abort();return reinterpret_cast<uintptr_t>(InitializeZone(object,name->text));}
        if(!std::strcmp(selector,"name"))return reinterpret_cast<uintptr_t>(object->children.at(0));
        if(!std::strcmp(selector,"data"))return reinterpret_cast<uintptr_t>(object->children.at(1));
    }
    if(object->kind==Kind::Data){if(!std::strcmp(selector,"bytes"))return reinterpret_cast<uintptr_t>(object->bytes.data());if(!std::strcmp(selector,"length"))return object->bytes.size();}
    if(object->kind==Kind::Array){if(!std::strcmp(selector,"count"))return object->children.size();if(!std::strcmp(selector,"objectAtIndex:")){if(argument>=object->children.size())std::abort();return reinterpret_cast<uintptr_t>(object->children[argument]);}}
    std::fprintf(stderr,"Unsupported Foundation selector: %s\n",selector);std::abort();
}
}
