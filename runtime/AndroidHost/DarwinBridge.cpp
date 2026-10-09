#include "DarwinBridge.h"
#include "DarwinString.h"
#include "DarwinSystem.h"
#include <android/log.h>
#include <cmath>
#include <cstdio>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <fcntl.h>
#include <locale.h>
#include <dlfcn.h>
#include <signal.h>
#include <ucontext.h>
#include <string>
#include <unordered_map>

extern char** environ;
extern "C" void DiscoDarwinSnprintf(),DiscoDarwinSprintf(),DiscoDarwinOpen(),DiscoDarwinStackProbe(),DiscoGCSpill();
extern "C" int DiscoSnprintf(char*,size_t,const char*,const uint8_t*);
extern "C" int DiscoVfprintf(FILE*,const char*,const uint8_t*);
namespace DiscoDarwin {
uint32_t MachThreadSelf();int MachPortRelease(uint32_t,uint32_t);int ThreadSuspend(uint32_t);int ThreadResume(uint32_t);int ThreadGetState(uint32_t,int,void*,uint32_t*);extern uint32_t machTask;
inline uintptr_t mappedBase=0,mappedSize=0;
void ConfigureImage(void* base,size_t bytes){mappedBase=reinterpret_cast<uintptr_t>(base);mappedSize=bytes;}
void Crash(int signal,siginfo_t* info,void* context){auto* u=static_cast<ucontext_t*>(context);uintptr_t pc=u->uc_mcontext.pc,lr=u->uc_mcontext.regs[30];__android_log_print(ANDROID_LOG_FATAL,"DiscoRuntime","native fault signal=%d address=%p pc=%llx image_pc=%llx image_lr=%llx",signal,info->si_addr,(unsigned long long)pc,(unsigned long long)(pc-mappedBase),(unsigned long long)(lr-mappedBase));struct sigaction action{};action.sa_handler=SIG_DFL;sigaction(signal,&action,nullptr);raise(signal);}
void InstallCrashReport(){struct sigaction action{};action.sa_sigaction=Crash;action.sa_flags=SA_SIGINFO;sigemptyset(&action.sa_mask);sigaction(SIGSEGV,&action,nullptr);sigaction(SIGBUS,&action,nullptr);sigaction(SIGILL,&action,nullptr);}
inline void* New(size_t n){void* p=std::malloc(n?n:1);if(!p)std::abort();return p;}
inline void Delete(void* p){std::free(p);}
inline void Assert(const char* function,const char* file,int line,const char* condition){__android_log_print(ANDROID_LOG_FATAL,"DiscoRuntime","foreign assertion %s:%d %s: %s",file,line,function,condition);std::abort();}
inline int ExecutablePath(char* buffer,uint32_t* size){char path[4096];ssize_t n=readlink("/proc/self/exe",path,sizeof(path)-1);if(n<0)return -1;path[n]=0;if(!size)return -1;if(!buffer||*size<uint32_t(n+1)){*size=n+1;return -1;}std::memcpy(buffer,path,n+1);return 0;}
inline uint32_t ImageCount(){return 1;}
inline const void* ImageHeader(uint32_t n){return n?nullptr:reinterpret_cast<void*>(mappedBase);}
inline intptr_t ImageSlide(uint32_t n){return n?0:mappedBase;}
inline const char* ImageName(uint32_t n){return n?nullptr:"GameAssembly.dylib";}
inline const void* Section(const void* header,const char* segment,const char* section){if(reinterpret_cast<uintptr_t>(header)!=mappedBase)return nullptr;auto* bytes=static_cast<const uint8_t*>(header);uint32_t count,length;std::memcpy(&count,bytes+16,4);std::memcpy(&length,bytes+20,4);if(length>mappedSize-32)return nullptr;size_t at=32;for(unsigned n=0;n<count;++n){uint32_t command,size;std::memcpy(&command,bytes+at,4);std::memcpy(&size,bytes+at+4,4);if(size<8||at+size>32+length)return nullptr;if(command==0x19&&size>=72){uint32_t sections;std::memcpy(&sections,bytes+at+64,4);if(72ULL+80ULL*sections>size)return nullptr;for(unsigned i=0;i<sections;++i){auto* s=bytes+at+72+i*80;if(!std::strncmp(reinterpret_cast<const char*>(s),section,16)&&!std::strncmp(reinterpret_cast<const char*>(s+16),segment,16))return s;}}at+=size;}return nullptr;}
inline void Zero(void* p,size_t n){std::memset(p,0,n);}
inline void Pattern16(void* p,const void* pattern,size_t n){auto* dst=static_cast<uint8_t*>(p);for(size_t at=0;at<n;at+=16)std::memcpy(dst+at,pattern,std::min(size_t(16),n-at));}
inline void* MoveChecked(void* p,const void* q,size_t n,size_t capacity){if(n>capacity)std::abort();return std::memmove(p,q,n);}
inline void* SetChecked(void* p,int value,size_t n,size_t capacity){if(n>capacity)std::abort();return std::memset(p,value,n);}
inline int CancelState(int state,int* old){static thread_local int current=1;if(state!=0&&state!=1)return EINVAL;if(old)*old=current;current=state;return 0;}
inline int* Error(){return &errno;}
inline int LocaleCategory(int c){return c==0?LC_ALL:c==1?LC_COLLATE:c==2?LC_CTYPE:c==3?LC_MONETARY:c==4?LC_NUMERIC:c==5?LC_TIME:c==6?LC_MESSAGES:-1;}
inline char* SetLocale(int category,const char* value){int c=LocaleCategory(category);if(c<0)return nullptr;return setlocale(c,value);}
inline locale_t NewLocale(int mask,const char* name,locale_t base){if(mask&~63){errno=EINVAL;return nullptr;}int native=0;const int bits[]={LC_COLLATE_MASK,LC_CTYPE_MASK,LC_MONETARY_MASK,LC_NUMERIC_MASK,LC_TIME_MASK,LC_MESSAGES_MASK};for(int i=0;i<6;++i)if(mask&(1<<i))native|=bits[i];return newlocale(native,name,base);}
struct ThreadAttr{pthread_attr_t value;ThreadAttr(){pthread_attr_init(&value);}~ThreadAttr(){pthread_attr_destroy(&value);}};
inline std::unordered_map<void*,std::shared_ptr<ThreadAttr>> threadAttributes;
inline int ThreadAttrInit(void* p){if(!p)return EINVAL;Get(threadAttributes,p);return 0;}
inline int ThreadAttrDestroy(void* p){std::lock_guard<std::mutex> lock(tableLock);threadAttributes.erase(p);return 0;}
inline int ThreadCreate(pthread_t* out,void* attr,void*(*entry)(void*),void* argument){auto a=attr?Get(threadAttributes,attr):std::shared_ptr<ThreadAttr>();return pthread_create(out,a?&a->value:nullptr,entry,argument);}
inline int ThreadName(const char* name){return pthread_setname_np(pthread_self(),name);}
inline void* Map(void* address,size_t n,int prot,int flags,int fd,int64_t offset){if(flags&0x1000){flags=(flags&~0x1000)|MAP_ANONYMOUS;}if(flags&~(MAP_PRIVATE|MAP_SHARED|MAP_FIXED|MAP_ANONYMOUS)){errno=EINVAL;return MAP_FAILED;}return mmap(address,n,prot,flags,fd,offset);}
struct Stat {int32_t device;uint16_t mode,links;uint64_t inode;uint32_t uid,gid;int32_t rdev,pad;int64_t times[8];int64_t size,blocks;int32_t blockSize;uint32_t flags,generation,spare;int64_t spare64[2];};
static_assert(sizeof(Stat)==144,"Darwin stat layout");
inline void ConvertStat(const struct stat& from,Stat* to){std::memset(to,0,sizeof(*to));to->device=from.st_dev;to->mode=from.st_mode;to->links=from.st_nlink;to->inode=from.st_ino;to->uid=from.st_uid;to->gid=from.st_gid;to->rdev=from.st_rdev;to->times[0]=from.st_atim.tv_sec;to->times[1]=from.st_atim.tv_nsec;to->times[2]=from.st_mtim.tv_sec;to->times[3]=from.st_mtim.tv_nsec;to->times[4]=from.st_ctim.tv_sec;to->times[5]=from.st_ctim.tv_nsec;to->size=from.st_size;to->blocks=from.st_blocks;to->blockSize=from.st_blksize;}
inline int FileStat(int fd,Stat* to){struct stat s;int r=fstat(fd,&s);if(!r)ConvertStat(s,to);return r;}
inline int PathStat(const char* p,Stat* to){struct stat s;int r=stat(p,&s);if(!r)ConvertStat(s,to);return r;}
inline int LinkStat(const char* p,Stat* to){struct stat s;int r=lstat(p,&s);if(!r)ConvertStat(s,to);return r;}
extern "C" int DiscoOpen(const char* path,int flags,const uint8_t* args){
    if(flags&~(3|8|0x200|0x400|0x800|0x1000000)){errno=EINVAL;return -1;}
    int native=(flags&3)|((flags&8)?O_APPEND:0)|((flags&0x200)?O_CREAT:0)|((flags&0x400)?O_TRUNC:0)|((flags&0x800)?O_EXCL:0)|((flags&0x1000000)?O_CLOEXEC:0);
    uint32_t mode=0;if(flags&0x200)std::memcpy(&mode,args,4);
    int fd=open(path,native,mode);__android_log_print(ANDROID_LOG_INFO,"DiscoRuntime","open %s -> %d",path,fd);return fd;
}
inline int Sysctl(const int* mib,unsigned count,void* output,size_t* size,const void* input,size_t inputSize){
    timespec real{},up{};clock_gettime(CLOCK_REALTIME,&real);clock_gettime(CLOCK_BOOTTIME,&up);
    int64_t seconds=real.tv_sec-up.tv_sec,nanos=real.tv_nsec-up.tv_nsec;if(nanos<0){--seconds;nanos+=1000000000;}
    return QuerySystem(mib,count,output,size,input,inputSize,sysconf(_SC_NPROCESSORS_ONLN),{seconds,int32_t(nanos/1000),0});
}
inline int GetTime(Timeval* out,void* zone){if(zone){errno=EINVAL;return -1;}timeval value{};int r=gettimeofday(&value,nullptr);if(!r&&out)*out={value.tv_sec,int32_t(value.tv_usec),0};return r;}
[[noreturn]] inline void StackFailure(){__android_log_print(ANDROID_LOG_FATAL,"DiscoRuntime","Foreign stack canary failed");std::abort();}
inline long Sysconf(int name){switch(name){case 29:return sysconf(_SC_PAGESIZE);case 58:return sysconf(_SC_NPROCESSORS_ONLN);default:__android_log_print(ANDROID_LOG_FATAL,"DiscoRuntime","unsupported Darwin sysconf %d",name);std::abort();}}
inline char** environment=nullptr;
inline char*** Environ(){environment=::environ;return &environment;}
inline void* StackTop(pthread_t thread){pthread_attr_t attr;if(pthread_getattr_np(thread,&attr))return nullptr;void* base;size_t size;int r=pthread_attr_getstack(&attr,&base,&size);pthread_attr_destroy(&attr);return r?nullptr:static_cast<char*>(base)+size;}
inline uintptr_t stackGuard=0x98ad2749bc517e00ULL;
inline FILE* errorStream=stderr;

uintptr_t ResolveAdditional(const char* name){
#define R(symbol,function) if(!std::strcmp(name,symbol))return reinterpret_cast<uintptr_t>(function)
    R("__Znwm",&New);R("__Znam",&New);R("__ZdlPv",&Delete);R("__ZdaPv",&Delete);
    R("_pthread_mutex_init",&MutexInit);R("_pthread_mutex_destroy",&MutexDestroy);R("_pthread_mutex_lock",&MutexLock);R("_pthread_mutex_unlock",&MutexUnlock);
    R("_pthread_mutexattr_init",&AttrInit);R("_pthread_mutexattr_settype",&AttrType);R("_pthread_mutexattr_destroy",&AttrDestroy);
    R("_pthread_cond_init",&CondInit);R("_pthread_cond_destroy",&CondDestroy);R("_pthread_cond_signal",&CondSignal);R("_pthread_cond_broadcast",&CondBroadcast);R("_pthread_cond_wait",&CondWait);R("_pthread_cond_timedwait",&CondTimedWait);R("_pthread_cond_timedwait_relative_np",&CondRelativeWait);
    R("_pthread_rwlock_init",&RWInit);R("_pthread_rwlock_destroy",&RWDestroy);R("_pthread_rwlock_rdlock",&RWRead);R("_pthread_rwlock_wrlock",&RWWrite);R("_pthread_rwlock_unlock",&RWUnlock);
    R("_pthread_key_create",&KeyCreate);R("_pthread_key_delete",&KeyDelete);R("_pthread_getspecific",&KeyGet);R("_pthread_setspecific",&KeySet);
    R("_pthread_attr_init",&ThreadAttrInit);R("_pthread_attr_destroy",&ThreadAttrDestroy);R("_pthread_create",&ThreadCreate);R("_pthread_detach",&pthread_detach);R("_pthread_setname_np",&ThreadName);R("_pthread_atfork",&pthread_atfork);R("_pthread_self",&pthread_self);R("_pthread_get_stackaddr_np",&StackTop);R("_pthread_setcancelstate",&CancelState);
    R("_dispatch_semaphore_create",&SemaphoreCreate);R("_dispatch_semaphore_signal",&SemaphoreSignal);R("_dispatch_semaphore_wait",&SemaphoreWait);R("_dispatch_release",&SemaphoreRelease);
    R("_mach_thread_self",&MachThreadSelf);R("_mach_port_deallocate",&MachPortRelease);R("_mach_task_self_",&machTask);R("_thread_suspend",&ThreadSuspend);R("_thread_resume",&ThreadResume);R("_thread_get_state",&ThreadGetState);R("_mach_absolute_time",&AbsoluteTime);R("___cxa_guard_acquire",&GuardAcquire);R("___cxa_guard_release",&GuardRelease);R("___cxa_guard_abort",&GuardAbort);R("___cxa_atexit",&AtExit);
    R("__ZNSt3__15mutexD1Ev",&MutexDtor);R("__ZNSt3__118condition_variableD1Ev",&CondDtor);
    R("__ZNSt3__112basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEED1Ev",&StringDestroy);
    R("__ZNSt3__112basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEE7reserveEm",&StringReserve);
    R("__ZNSt3__112basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEE6insertEmPKc",&StringInsert);
    R("__ZNSt3__112basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEEC1ERKS5_mmRKS4_",&StringSubstring);
    R("__ZNKSt3__112basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEE7compareEmmPKcm",&StringCompareRange);
    R("__ZNSt3__112basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEE6assignEPKc",&StringAssign);
    R("__ZNSt3__112basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEE6assignEPKcm",&StringAssignN);
    R("__ZNSt3__112basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEEaSERKS5_",&StringCopyAssign);
    R("__ZNSt3__112basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEEC1ERKS5_",&StringCopyConstruct);
    R("__ZNSt3__112basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEE6appendEPKc",&StringAppend);
    R("__ZNSt3__112basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEE6appendEPKcm",&StringAppendN);
    R("__ZNSt3__112basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEE6appendEmc",&StringAppendChar);
    R("__ZNSt3__112basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEE9push_backEc",&StringPush);
    R("__ZNSt3__112basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEE6resizeEmc",&StringResize);
    R("__ZNKSt3__112basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEE7compareEPKc",&StringCompare);
    R("__ZNKSt3__112basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEE4findEcm",&StringFind);
    R("__ZNKSt3__112basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEE5rfindEcm",&StringRFind);
    R("__NSGetExecutablePath",&ExecutablePath);R("__dyld_image_count",&ImageCount);R("__dyld_get_image_header",&ImageHeader);R("__dyld_get_image_vmaddr_slide",&ImageSlide);R("__dyld_get_image_name",&ImageName);R("_getsectbynamefromheader_64",&Section);R("_sprintf",&DiscoDarwinSprintf);R("_snprintf",&DiscoDarwinSnprintf);R("_vsnprintf",&DiscoSnprintf);R("_vfprintf",&DiscoVfprintf);R("___chkstk_darwin",&DiscoDarwinStackProbe);R("__setjmp",&DiscoGCSpill);R("_bzero",&Zero);R("_memset_pattern16",&Pattern16);R("___memmove_chk",&MoveChecked);R("___memset_chk",&SetChecked);R("___assert_rtn",&Assert);R("___error",&Error);R("___stack_chk_guard",&stackGuard);R("___stderrp",&errorStream);
    R("_mmap",&Map);R("_fstat",&FileStat);R("_stat",&PathStat);R("_lstat",&LinkStat);R("_open",&DiscoDarwinOpen);R("_sysctl",&Sysctl);R("_gettimeofday",&GetTime);R("_atexit",&PlainAtExit);R("___stack_chk_fail",&StackFailure);R("_sysconf",&Sysconf);R("_setlocale",&SetLocale);R("_newlocale",&NewLocale);R("_freelocale",&freelocale);R("__NSGetEnviron",&Environ);
#define C(function) R("_" #function,&function)
    C(gethostname);C(calloc);C(realloc);C(memcpy);C(memmove);C(memset);C(memcmp);R("_memchr",static_cast<void*(*)(void*,int,size_t)>(&memchr));C(strlen);C(strcmp);C(strncmp);C(strcpy);C(strncpy);R("_strchr",static_cast<char*(*)(char*,int)>(&strchr));R("_strrchr",static_cast<char*(*)(char*,int)>(&strrchr));R("_strstr",static_cast<char*(*)(char*,const char*)>(&strstr));C(strlcpy);C(strtol);C(strtoul);C(atoi);C(atol);C(getenv);C(setenv);C(unsetenv);
    C(dup);C(ftruncate);C(clock);C(bsearch);C(close);C(read);C(write);C(lseek);C(munmap);C(mprotect);C(getpagesize);C(getcwd);C(access);C(unlink);C(fopen);C(fclose);C(fflush);C(fread);C(fwrite);C(ftello);C(fseeko);C(posix_memalign);C(nanosleep);C(time);C(sched_yield);C(abort);
#undef C
#undef R
    return 0;
}
}
