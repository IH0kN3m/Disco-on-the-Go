#pragma once
#include <cstdint>
#include <cstring>
namespace DiscoDirectory {
struct Entry {uint64_t inode,offset;uint16_t recordLength,nameLength;uint8_t type;char name[1024];};
static_assert(sizeof(Entry)==1048,"Darwin directory entry layout");
inline bool Convert(Entry& entry,uint64_t inode,uint64_t offset,uint8_t type,const char* name){
    if(!name)return false;size_t n=std::strlen(name);if(n>=sizeof(entry.name))return false;
    std::memset(&entry,0,sizeof(entry));entry.inode=inode;entry.offset=offset;entry.type=type;entry.nameLength=n;
    entry.recordLength=(21+n+1+3)&~3;std::memcpy(entry.name,name,n+1);return true;
}
}
