// Apple ARM64 libc++ alternate string layout: 24 bytes, 22-byte SSO capacity.
// Original adapter implementation; host std::string objects never cross the ABI.
#pragma once
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <string>
#include <limits>
namespace DiscoDarwin {
struct String {
    uint8_t bytes[24];
    bool Long()const{return bytes[23]&128;}
    uint64_t Word(unsigned n)const{uint64_t v;std::memcpy(&v,bytes+n*8,8);return v;}
    size_t Size()const{return Long()?Word(1):bytes[23];}
    char* Data(){return Long()?reinterpret_cast<char*>(Word(0)):reinterpret_cast<char*>(bytes);}
    const char* Data()const{return const_cast<String*>(this)->Data();}
    size_t Capacity()const{return Long()?(Word(2)&~(1ULL<<63))-1:22;}
    void Write(const char* text,size_t n){
        if(n>64*1024*1024)std::abort();std::string copy(text,n);bool oldLong=Long();char* old=Data();
        if(n<=22){std::memset(bytes,0,24);std::memcpy(bytes,copy.data(),n);bytes[23]=n;}
        else{uint64_t capacity=(n+16)&~uint64_t(15);auto* data=static_cast<char*>(std::malloc(capacity));if(!data)std::abort();std::memcpy(data,copy.data(),n);data[n]=0;uint64_t words[]={reinterpret_cast<uint64_t>(data),n,capacity|(1ULL<<63)};std::memcpy(bytes,words,24);}
        if(oldLong)std::free(old);
    }
};
static_assert(sizeof(String)==24,"Apple string layout");
inline bool StringGrowthBounds(const String* s,size_t capacity,size_t delta,size_t size,size_t prefix,size_t removed,size_t added){
    constexpr size_t limit=64*1024*1024;
    return capacity==s->Capacity()&&capacity<=limit/2&&delta<=limit-capacity&&
        size<=capacity&&prefix<=size&&removed<=size-prefix&&added<=limit-(size-removed)&&
        size-removed+added<=std::max(capacity+delta,capacity*2);
}
inline void StringGrow(String* s,size_t capacity,size_t delta,size_t size,size_t prefix,size_t removed,size_t added){
    if(!StringGrowthBounds(s,capacity,delta,size,prefix,removed,added))std::abort();
    size_t storage=(std::max(capacity+delta,capacity*2)+16)&~size_t(15);
    char* data=static_cast<char*>(std::malloc(storage));if(!data)std::abort();
    const char* old=s->Data();bool wasLong=s->Long();uint64_t sizeWord=s->Word(1);
    std::memcpy(data,old,prefix);
    std::memcpy(data+prefix+added,old+prefix+removed,size-prefix-removed);
    if(wasLong)std::free(const_cast<char*>(old));
    // libc++'s legacy __grow_by deliberately leaves the size word unchanged.
    // Its caller writes the inserted bytes, final size and terminating NUL.
    uint64_t words[]={reinterpret_cast<uint64_t>(data),sizeWord,uint64_t(storage)|(1ULL<<63)};
    std::memcpy(s,words,24);
}
inline String* StringDestroy(String* s){if(s->Long())std::free(s->Data());std::memset(s->bytes,0,24);return s;}
inline String* StringAssignN(String* s,const char* p,size_t n){s->Write(p,n);return s;}
inline String* StringAssign(String* s,const char* p){return StringAssignN(s,p,std::strlen(p));}
inline String* StringCopyAssign(String* s,const String* p){return StringAssignN(s,p->Data(),p->Size());}
inline String* StringCopyConstruct(String* s,const String* p){std::memset(s,0,24);s->Write(p->Data(),p->Size());return s;}
inline String* StringAppendN(String* s,const char* p,size_t n){std::string value(s->Data(),s->Size());value.append(p,n);s->Write(value.data(),value.size());return s;}
inline String* StringAppend(String* s,const char* p){return StringAppendN(s,p,std::strlen(p));}
inline String* StringAppendChar(String* s,size_t count,char value){std::string added(count,value);return StringAppendN(s,added.data(),added.size());}
inline void StringPush(String* s,char value){StringAppendN(s,&value,1);}
inline void StringResize(String* s,size_t n,char value){std::string copy(s->Data(),s->Size());copy.resize(n,value);s->Write(copy.data(),copy.size());}
inline void StringReserve(String* s,size_t n){if(n<=s->Capacity())return;if(n>64*1024*1024)std::abort();size_t size=s->Size();uint64_t capacity=(n+16)&~uint64_t(15);char* p=static_cast<char*>(std::malloc(capacity));if(!p)std::abort();std::memcpy(p,s->Data(),size);p[size]=0;if(s->Long())std::free(s->Data());uint64_t words[]={reinterpret_cast<uint64_t>(p),size,capacity|(1ULL<<63)};std::memcpy(s,words,24);}
inline String* StringInsert(String* s,size_t pos,const char* text){if(pos>s->Size())std::abort();std::string value(s->Data(),s->Size());value.insert(pos,text);s->Write(value.data(),value.size());return s;}
inline String* StringSubstring(String* s,const String* other,size_t pos,size_t count,const void*){if(pos>other->Size())std::abort();std::memset(s,0,24);s->Write(other->Data()+pos,std::min(count,other->Size()-pos));return s;}
inline int StringCompareRange(const String* s,size_t pos,size_t count,const char* p,size_t n){if(pos>s->Size())std::abort();return std::string(s->Data(),s->Size()).compare(pos,count,p,n);}
inline int StringCompare(const String* s,const char* p){return std::string(s->Data(),s->Size()).compare(p);}
inline size_t StringFind(const String* s,char c,size_t at){return std::string(s->Data(),s->Size()).find(c,at);}
inline size_t StringRFind(const String* s,char c,size_t at){return std::string(s->Data(),s->Size()).rfind(c,at);}
}
