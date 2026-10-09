// Original reader/mapper for our validated, private staging format, not a general Mach-O loader.
#pragma once
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <string>
#include <vector>
#include <set>
#include <algorithm>
#include <sys/mman.h>
#include <unistd.h>

namespace DiscoMap {
inline void Require(bool condition, const char* why) { if(!condition) throw std::runtime_error(why); }
struct Segment { uint64_t address,size,offset,fileSize,protection; };
struct Rebase { uint64_t address,target; };
struct Binding { uint64_t address; uint32_t name; int32_t ordinal; int64_t addend; uint32_t flags,kind; };
struct Export { uint64_t address; uint32_t name,reserved; };
class Reader {
    const uint8_t* data; size_t size,at=0;
public:
    Reader(const uint8_t* p,size_t n):data(p),size(n) {}
    const uint8_t* Take(size_t n) {Require(n<=size-at,"Truncated runtime pack");auto p=data+at;at+=n;return p;}
    template<class T> T Read(){T result;std::memcpy(&result,Take(sizeof(T)),sizeof(T));return result;}
    bool End() const {return at==size;}
};
class Image {
    uint8_t* memory=nullptr;
public:
    std::vector<Segment> segments;
    std::vector<Rebase> rebases;
    std::vector<Binding> bindings;
    std::vector<Export> exports;
    std::vector<uint64_t> initializers;
    std::string strings;
    const uint8_t* file=nullptr;uint64_t fileSize=0,span=0;
    bool executableUnchanged=false;
    Image(const uint8_t* data,size_t size) {
        Require(data && size>=40 && size<=128*1024*1024,"Invalid runtime pack size");
        Reader r(data,size);Require(std::memcmp(r.Take(8),"DSCMAP01",8)==0,"Unsupported runtime pack version");
        auto ns=r.Read<uint32_t>(),nr=r.Read<uint32_t>(),nb=r.Read<uint32_t>(),ne=r.Read<uint32_t>(),ni=r.Read<uint32_t>(),nt=r.Read<uint32_t>();
        fileSize=r.Read<uint64_t>();
        Require(ns>0 && ns<=16 && nr<=1000000 && nb<=10000 && ne<=100000 && ni<=1024 && nt<=1024*1024 && fileSize<=64*1024*1024,"Runtime pack count exceeds bound");
        for(unsigned i=0;i<ns;++i)segments.push_back(r.Read<Segment>());
        for(unsigned i=0;i<nr;++i)rebases.push_back(r.Read<Rebase>());
        for(unsigned i=0;i<nb;++i)bindings.push_back(r.Read<Binding>());
        for(unsigned i=0;i<ne;++i)exports.push_back(r.Read<Export>());
        for(unsigned i=0;i<ni;++i)initializers.push_back(r.Read<uint64_t>());
        strings.assign(reinterpret_cast<const char*>(r.Take(nt)),nt);file=r.Take(fileSize);
        Require(r.End(),"Trailing runtime pack data");
        uint64_t lowest=UINT64_MAX;
        for(auto& s:segments) {
            Require(s.size>0 && s.address<=256*1024*1024 && s.size<=256*1024*1024-s.address &&
                    s.fileSize<=s.size && s.offset<=fileSize && s.fileSize<=fileSize-s.offset &&
                    (s.address|s.size)%16384==0 && (s.protection==1 || s.protection==3 || s.protection==5),"Invalid segment");
            span=std::max(span,s.address+s.size);lowest=std::min(lowest,s.address);
        }
        Require(lowest==0,"Image base must be zero");
        for(size_t i=0;i<segments.size();++i)for(size_t j=i+1;j<segments.size();++j)
            Require(segments[i].address+segments[i].size<=segments[j].address || segments[j].address+segments[j].size<=segments[i].address,"Overlapping segments");
        for(auto& s:segments)Owner(s.address,s.size);
        std::set<uint64_t> seen;
        for(auto& f:rebases) {
            const auto& s=Owner(f.address,8,2);Owner(f.target&~(1ULL<<63),1);
            Require(f.address%8==0 && seen.insert(f.address).second && f.address-s.address+8<=s.fileSize,"Invalid rebase slot");
            uint64_t old;std::memcpy(&old,file+s.offset+f.address-s.address,8);
            Require(old==f.target,"Rebase does not match source pointer");
        }
        for(auto& b:bindings) {
            Owner(b.address,8,2);Name(b.name);
            Require(b.address%8==0 && b.ordinal>=-3 && b.ordinal<=64 && b.kind<=2 && !(b.flags&~9u),"Invalid binding");
        }
        std::set<std::string> names;
        for(auto& e:exports){Owner(e.address,1);Require(!e.reserved && names.insert(Name(e.name)).second,"Duplicate/invalid export");}
        for(auto a:initializers)Owner(a,4,4);
    }
    Image(const Image&)=delete;Image& operator=(const Image&)=delete;
    ~Image(){if(memory)munmap(memory,span);}
    const Segment& Owner(uint64_t address,uint64_t bytes,int permission=0) const {
        const Segment* result=nullptr;
        for(auto& s:segments)if(address>=s.address && address-s.address<=s.size && bytes<=s.size-(address-s.address)) {
            Require(!result,"Ambiguous segment ownership");result=&s;
        }
        Require(bytes && result && (result->protection&permission)==unsigned(permission),"Address ownership/protection failure");return *result;
    }
    const char* Name(uint32_t offset) const {
        Require(offset<strings.size(),"Symbol offset outside string table");
        auto end=strings.find('\0',offset);Require(end!=std::string::npos && end>offset && end-offset<4096,"Invalid symbol name");
        return strings.c_str()+offset;
    }
    void Map() {
        Require(!memory,"Image already mapped");long page=sysconf(_SC_PAGESIZE);
        Require(page==4096 || page==16384,"Unsupported host page size");
        void* p=mmap(nullptr,span,PROT_NONE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
        Require(p!=MAP_FAILED,"Image reservation failed");memory=static_cast<uint8_t*>(p);
        for(auto& s:segments) {
            Require(mprotect(memory+s.address,s.size,PROT_READ|PROT_WRITE)==0,"Segment staging protection failed");
            std::memcpy(memory+s.address,file+s.offset,s.fileSize);
        }
        for(auto& f:rebases){uint64_t value=reinterpret_cast<uint64_t>(memory)+(f.target&~(1ULL<<63));value|=f.target&(1ULL<<63);std::memcpy(memory+f.address,&value,8);}
    }
    void Bind(uint64_t address,uintptr_t value){Owner(address,8,2);Require(memory,"Image not mapped");std::memcpy(memory+address,&value,8);}
    void Seal() {
        Require(memory,"Image not mapped");executableUnchanged=true;
        for(auto& s:segments) {
            if(s.protection&4) {
                executableUnchanged &= std::memcmp(memory+s.address,file+s.offset,s.fileSize)==0;
                __builtin___clear_cache(reinterpret_cast<char*>(memory+s.address),reinterpret_cast<char*>(memory+s.address+s.size));
            }
            Require(mprotect(memory+s.address,s.size,s.protection)==0,"Final segment protection failed");
        }
        Require(executableUnchanged,"Executable bytes changed");
    }
    void* At(uint64_t address,size_t size=1,int permission=0)const{Owner(address,size,permission);Require(memory,"Image not mapped");return memory+address;}
    void* Symbol(const char* name)const{for(auto&e:exports)if(!std::strcmp(Name(e.name),name))return At(e.address,4,4);throw std::runtime_error("Missing executable export");}
};
static_assert(sizeof(Segment)==40 && sizeof(Rebase)==16 && sizeof(Binding)==32 && sizeof(Export)==16,"Staging record layout");
}
