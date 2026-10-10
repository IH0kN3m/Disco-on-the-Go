#include "DarwinBridge.h"
#include "DarwinString.h"
#include "DarwinSystem.h"
#include "DarwinLocale.h"
#include "DarwinDirectory.h"
#include "DarwinFoundation.h"
#ifdef DISCO_MAPPED_RUNTIME
namespace DiscoRuntime {void* TryOpenPlugin(const char*);bool PluginHandle(void*);void* PluginSymbol(void*,const char*);}
#endif
#include <android/log.h>
#include <cmath>
#include <cwctype>
#include <malloc.h>
#include <dirent.h>
#include <cxxabi.h>
#include <unwind.h>
#include <sys/utsname.h>
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
extern "C" _Unwind_Reason_Code __gxx_personality_v0(int,_Unwind_Action,uint64_t,_Unwind_Exception*,_Unwind_Context*);
extern "C" char DiscoClassVtable[] asm("_ZTVN10__cxxabiv117__class_type_infoE");
extern "C" char DiscoSingleVtable[] asm("_ZTVN10__cxxabiv120__si_class_type_infoE");
extern "C" char DiscoMultipleVtable[] asm("_ZTVN10__cxxabiv121__vmi_class_type_infoE");
extern "C" void DiscoDarwinSnprintf(),DiscoDarwinSprintf(),DiscoDarwinOpen(),DiscoDarwinStackProbe(),DiscoGCSpill(),DiscoPluginSetjmp(),DiscoPluginLongjmp(),DiscoDarwinPrintf(),DiscoDarwinFcntl();
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

struct Trace {void** output;int size,count;};
inline _Unwind_Reason_Code TraceFrame(_Unwind_Context* frame,void* opaque){auto& trace=*static_cast<Trace*>(opaque);uintptr_t ip=_Unwind_GetIP(frame);if(ip&&trace.count<trace.size)trace.output[trace.count++]=reinterpret_cast<void*>(ip);return trace.count==trace.size?_URC_END_OF_STACK:_URC_NO_REASON;}
inline int Backtrace(void** output,int size){if(!output||size<=0)return 0;Trace trace{output,size,0};_Unwind_Backtrace(TraceFrame,&trace);return trace.count;}
struct SinCos {float sine,cosine;};
inline SinCos SinCosFloat(float v){return {sinf(v),cosf(v)};}
inline float ExpTen(float v){return powf(10,v);}
struct Uname {char system[256],node[256],release[256],version[256],machine[256];};
inline int SystemName(Uname* out){if(!out){errno=EFAULT;return -1;}utsname value{};int r=uname(&value);if(r)return r;std::memset(out,0,sizeof(*out));strlcpy(out->system,value.sysname,256);strlcpy(out->node,value.nodename,256);strlcpy(out->release,value.release,256);strlcpy(out->version,value.version,256);strlcpy(out->machine,value.machine,256);return 0;}
inline DiscoDirectory::Entry* ReadDirectory(DIR* directory){
    auto* native=readdir(directory);if(!native)return nullptr;
    static thread_local DiscoDirectory::Entry result;
    if(!DiscoDirectory::Convert(result,native->d_ino,native->d_off,native->d_type,native->d_name)){errno=ENAMETOOLONG;return nullptr;}return &result;
}
extern "C" int DiscoFcntl(int fd,int command,const uint8_t* arguments){
    int value=0;if(command==0||command==2||command==4)std::memcpy(&value,arguments,4);
    switch(command){
    case 0:return fcntl(fd,F_DUPFD,value);
    case 1:return fcntl(fd,F_GETFD);
    case 2:return fcntl(fd,F_SETFD,value);
    case 3:{int flags=fcntl(fd,F_GETFL);if(flags<0)return flags;return (flags&O_ACCMODE)|((flags&O_APPEND)?8:0)|((flags&O_NONBLOCK)?4:0);}
    case 4:if(value&~(3|4|8)){errno=EINVAL;return -1;}return fcntl(fd,F_SETFL,(value&3)|((value&8)?O_APPEND:0)|((value&4)?O_NONBLOCK:0));
    default:__android_log_print(ANDROID_LOG_FATAL,"DiscoRuntime","Unsupported Darwin fcntl command %d",command);std::abort();
    }
}
inline void SortIntegers(int* begin,int* end,void*){if(end<begin||size_t(end-begin)>16*1024*1024)std::abort();std::sort(begin,end);}
inline void* OpenLibrary(const char* path,int flags){
    if(flags&~15){__android_log_print(ANDROID_LOG_FATAL,"DiscoRuntime","Unsupported Darwin dlopen flags %x",flags);std::abort();}
#ifdef DISCO_MAPPED_RUNTIME
    if(void* plugin=DiscoRuntime::TryOpenPlugin(path))return plugin;
#endif
    int mode=(flags&2)?RTLD_NOW:RTLD_LAZY;if(flags&8)mode|=RTLD_GLOBAL;
    void* handle=dlopen(path,mode);
    __android_log_print(ANDROID_LOG_INFO,"DiscoRuntime","dlopen %s -> %s",path?path:"<process>",handle?"loaded":"unavailable");return handle;
}
inline void* LibrarySymbol(void* handle,const char* name){
#ifdef DISCO_MAPPED_RUNTIME
    if(DiscoRuntime::PluginHandle(handle))return DiscoRuntime::PluginSymbol(handle,name);
#endif
    // Darwin's default/next pseudo-handles differ from Bionic's values.
    if(handle==reinterpret_cast<void*>(intptr_t(-2)))handle=RTLD_DEFAULT;
    else if(handle==reinterpret_cast<void*>(intptr_t(-1)))handle=RTLD_NEXT;
    return dlsym(handle,name);
}
inline int CloseLibrary(void* handle){
#ifdef DISCO_MAPPED_RUNTIME
    if(DiscoRuntime::PluginHandle(handle))return 0; // Process-lifetime CPU codec callbacks.
#endif
    return dlclose(handle);
}
uintptr_t ResolveAdditional(const char* name){
#define R(symbol,function) if(!std::strcmp(name,symbol))return reinterpret_cast<uintptr_t>(function)
    R("_OBJC_CLASS_$_NSString",&DiscoFoundation::stringClass);R("_OBJC_CLASS_$_NSTimeZone",&DiscoFoundation::zoneClass);
    R("_objc_alloc",&DiscoFoundation::Alloc);R("_objc_msgSend",&DiscoFoundation::Message);R("_objc_release",&DiscoFoundation::Release);
    R("_objc_retainAutoreleasedReturnValue",&DiscoFoundation::Retain);R("_objc_retainAutorelease",&DiscoFoundation::RetainAutorelease);
    R("_objc_autoreleasePoolPush",&DiscoFoundation::PoolPush);R("_objc_autoreleasePoolPop",&DiscoFoundation::PoolPop);
    R("_CFLocaleCopyCurrent",&DiscoLocale::CopyCurrent);R("_CFLocaleGetIdentifier",&DiscoLocale::Identifier);R("_CFLocaleGetValue",&DiscoLocale::Value);R("_CFRelease",&DiscoLocale::Release);
    R("_CFStringGetLength",&DiscoLocale::Length);R("_CFStringGetMaximumSizeForEncoding",&DiscoLocale::MaxSize);R("_CFStringGetCString",&DiscoLocale::CString);R("_CFStringGetBytes",&DiscoLocale::Bytes);
    R("_kCFLocaleLanguageCode",&DiscoLocale::languageKeyPointer);R("_kCFLocaleCountryCode",&DiscoLocale::countryKeyPointer);R("_kCFLocaleScriptCode",&DiscoLocale::scriptKeyPointer);
    R("_readdir",&ReadDirectory);R("_fcntl",&DiscoDarwinFcntl);R("_setjmp",&DiscoPluginSetjmp);R("_longjmp",&DiscoPluginLongjmp);R("_printf",&DiscoDarwinPrintf);
    R("_backtrace",&Backtrace);R("_dlopen",&OpenLibrary);R("_dlsym",&LibrarySymbol);R("_dlclose",&CloseLibrary);R("_dlerror",&dlerror);
    R("___tolower",&towlower);R("___toupper",&towupper);
    R("__Unwind_Resume",&_Unwind_Resume);R("___gxx_personality_v0",&__gxx_personality_v0);
    R("___cxa_allocate_exception",&__cxxabiv1::__cxa_allocate_exception);R("___cxa_free_exception",&__cxxabiv1::__cxa_free_exception);
    R("___cxa_throw",&__cxxabiv1::__cxa_throw);R("___cxa_rethrow",&__cxxabiv1::__cxa_rethrow);R("___cxa_begin_catch",&__cxxabiv1::__cxa_begin_catch);R("___cxa_end_catch",&__cxxabiv1::__cxa_end_catch);R("___cxa_pure_virtual",&__cxxabiv1::__cxa_pure_virtual);
    R("__ZTVN10__cxxabiv117__class_type_infoE",DiscoClassVtable);R("__ZTVN10__cxxabiv120__si_class_type_infoE",DiscoSingleVtable);R("__ZTVN10__cxxabiv121__vmi_class_type_infoE",DiscoMultipleVtable);
    R("__ZSt9terminatev",&std::terminate);
    R("__Znwm",&New);R("__Znam",&New);R("__ZdlPv",&Delete);R("__ZdaPv",&Delete);
    R("_pthread_mutex_init",&MutexInit);R("_pthread_mutex_destroy",&MutexDestroy);R("_pthread_mutex_lock",&MutexLock);R("_pthread_mutex_unlock",&MutexUnlock);
    R("_pthread_mutexattr_init",&AttrInit);R("_pthread_mutexattr_settype",&AttrType);R("_pthread_mutexattr_destroy",&AttrDestroy);
    R("_pthread_cond_init",&CondInit);R("_pthread_cond_destroy",&CondDestroy);R("_pthread_cond_signal",&CondSignal);R("_pthread_cond_broadcast",&CondBroadcast);R("_pthread_cond_wait",&CondWait);R("_pthread_cond_timedwait",&CondTimedWait);R("_pthread_cond_timedwait_relative_np",&CondRelativeWait);
    R("_pthread_rwlock_init",&RWInit);R("_pthread_rwlock_destroy",&RWDestroy);R("_pthread_rwlock_rdlock",&RWRead);R("_pthread_rwlock_wrlock",&RWWrite);R("_pthread_rwlock_unlock",&RWUnlock);
    R("_pthread_key_create",&KeyCreate);R("_pthread_key_delete",&KeyDelete);R("_pthread_getspecific",&KeyGet);R("_pthread_setspecific",&KeySet);
    R("_pthread_attr_init",&ThreadAttrInit);R("_pthread_attr_destroy",&ThreadAttrDestroy);R("_pthread_create",&ThreadCreate);R("_pthread_detach",&pthread_detach);R("_pthread_setname_np",&ThreadName);R("_pthread_atfork",&pthread_atfork);R("_pthread_self",&pthread_self);R("_pthread_get_stackaddr_np",&StackTop);R("_pthread_setcancelstate",&CancelState);
    R("_dispatch_semaphore_create",&SemaphoreCreate);R("_dispatch_semaphore_signal",&SemaphoreSignal);R("_dispatch_semaphore_wait",&SemaphoreWait);R("_dispatch_release",&SemaphoreRelease);
    R("_mach_thread_self",&MachThreadSelf);R("_mach_port_deallocate",&MachPortRelease);R("_mach_task_self_",&machTask);R("_thread_suspend",&ThreadSuspend);R("_thread_resume",&ThreadResume);R("_thread_get_state",&ThreadGetState);R("_mach_absolute_time",&AbsoluteTime);R("___cxa_guard_acquire",&GuardAcquire);R("___cxa_guard_release",&GuardRelease);R("___cxa_guard_abort",&GuardAbort);R("___cxa_atexit",&AtExit);
    R("__ZNSt3__16__sortIRNS_6__lessIiiEEPiEEvT0_S5_T_",&SortIntegers);
    R("__ZNSt3__15mutex4lockEv",&MutexLock);R("__ZNSt3__15mutex6unlockEv",&MutexUnlock);R("__ZNSt3__15mutexD1Ev",&MutexDtor);R("__ZNSt3__118condition_variableD1Ev",&CondDtor);
    R("__ZNSt3__112basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEED1Ev",&StringDestroy);
    R("__ZNSt3__112basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEE7reserveEm",&StringReserve);
    R("__ZNSt3__112basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEE9__grow_byEmmmmmm",&StringGrow);
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
    R("_acos",static_cast<double(*)(double)>(&acos));C(acosf);R("_asin",static_cast<double(*)(double)>(&asin));C(asinf);R("_atan",static_cast<double(*)(double)>(&atan));R("_atan2",static_cast<double(*)(double,double)>(&atan2));C(atan2f);C(atanf);R("_cos",static_cast<double(*)(double)>(&cos));C(cosf);R("_cosh",static_cast<double(*)(double)>(&cosh));R("_exp",static_cast<double(*)(double)>(&exp));C(exp2f);R("_fmod",static_cast<double(*)(double,double)>(&fmod));C(fmodf);R("_hypot",static_cast<double(*)(double,double)>(&hypot));C(ldexpf);R("_log",static_cast<double(*)(double)>(&log));R("_log10",static_cast<double(*)(double)>(&log10));C(log10f);R("_logb",static_cast<double(*)(double)>(&logb));R("_modf",static_cast<double(*)(double,double*)>(&modf));R("_pow",static_cast<double(*)(double,double)>(&pow));C(powf);R("_scalbn",static_cast<double(*)(double,int)>(&scalbn));R("_sin",static_cast<double(*)(double)>(&sin));C(sinf);R("_sinh",static_cast<double(*)(double)>(&sinh));R("_tan",static_cast<double(*)(double)>(&tan));C(tanf);R("_tanh",static_cast<double(*)(double)>(&tanh));
    R("___sincosf_stret",&SinCosFloat);R("___exp10f",&ExpTen);R("_uname",&SystemName);
    C(opendir);C(closedir);C(_exit);C(ferror);C(fputs);C(puts);R("_malloc_size",&malloc_usable_size);
    C(chmod);C(mkdir);C(rename);C(rmdir);C(dup2);C(isatty);C(pipe);C(difftime);C(gmtime);C(localtime);C(mktime);C(strftime);
    C(dup);C(ftruncate);C(clock);C(bsearch);C(close);C(read);C(write);C(lseek);C(munmap);C(mprotect);C(getpagesize);C(getcwd);C(access);C(unlink);C(fopen);C(fclose);C(fflush);C(fread);C(fwrite);C(ftello);C(fseeko);C(posix_memalign);C(nanosleep);C(time);C(sched_yield);C(abort);
#undef C
#undef R
    return 0;
}
}
