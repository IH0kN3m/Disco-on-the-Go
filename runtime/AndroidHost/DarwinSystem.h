// Narrow Darwin sysctl contract, with supplied values for host-side tests.
#pragma once
#include <cstdint>
#include <cstring>
#include <cerrno>
#include <algorithm>
namespace DiscoDarwin {
struct Timeval {int64_t seconds;int32_t microseconds;int32_t padding;};
static_assert(sizeof(Timeval)==16,"Darwin timeval layout");
inline int QuerySystem(const int* mib,unsigned count,void* output,size_t* size,
                       const void* input,size_t inputSize,int cpus,Timeval boot){
    if(!mib||count!=2||!size||input||inputSize){errno=EINVAL;return -1;}
    const void* value=nullptr;size_t bytes=0;
    if(mib[0]==6&&mib[1]==3){value=&cpus;bytes=sizeof(cpus);}
    else if(mib[0]==1&&mib[1]==21){value=&boot;bytes=sizeof(boot);}
    else {errno=ENOENT;return -1;}
    size_t capacity=*size;*size=bytes;
    if(output){std::memcpy(output,value,std::min(capacity,bytes));if(capacity<bytes){errno=ENOMEM;return -1;}}
    return 0;
}
}
