// Explicit native startup experiment, followed by metadata invocation and GC checks.
#include "MappedImage.h"
#include "DarwinBridge.h"
#include <android/asset_manager.h>
#include <android/log.h>
#include <cstdlib>
#include <ctime>
#include <sstream>
#include <memory>
#ifdef DISCO_MAPPED_RUNTIME
#include "RuntimePins.h"
#include "MissingImports.h"
#endif

namespace DiscoDarwin {uintptr_t ResolveAdditional(const char*);void ConfigureImage(void*,size_t);void InstallCrashReport();bool ThreadBridgeSelfTest();}
#ifdef DISCO_MAPPED_RUNTIME
static uintptr_t imageBase=0;
extern "C" [[noreturn]] void DiscoUnsupportedTrap(unsigned n,uintptr_t caller){__android_log_print(ANDROID_LOG_FATAL,"DiscoRuntime","UNSUPPORTED IMPORT %s caller_image_offset=%llx",n<sizeof(missingNames)/sizeof(*missingNames)?missingNames[n]:"invalid",(unsigned long long)(caller-imageBase));std::abort();}
#endif
namespace {
std::atomic<unsigned> allocations{0},frees{0},clockQueries{0};
void* Allocate(size_t n){++allocations;return std::malloc(n);}
void Release(void* p){++frees;std::free(p);}
struct Timebase {uint32_t numerator,denominator;};
int TimebaseInfo(Timebase* value){++clockQueries;if(!value)return 4;value->numerator=1;value->denominator=1;return 0;}
uintptr_t Resolve(const char* symbol) {
    // Each entry is explicit. No dlsym-by-name assumption for Darwin ABI calls.
    if(!std::strcmp(symbol,"_malloc"))return reinterpret_cast<uintptr_t>(&Allocate);
    if(!std::strcmp(symbol,"_free"))return reinterpret_cast<uintptr_t>(&Release);
    if(!std::strcmp(symbol,"_mach_timebase_info"))return reinterpret_cast<uintptr_t>(&TimebaseInfo);
    return DiscoDarwin::ResolveAdditional(symbol);
}
void Phase(const char* phase){__android_log_print(ANDROID_LOG_INFO,"DiscoRuntime","%s",phase);}
}

std::string DiscoRuntimeReport(AAssetManager* manager,const char* dataPath) {
#ifndef DISCO_MAPPED_RUNTIME
    return "{\"included\":false}";
#else
    try {
        bool threadPassed=DiscoDarwin::ThreadBridgeSelfTest();
        DiscoMap::Require(threadPassed,"Collector thread bridge self-test failed");
        Phase("synthetic thread suspension/resume and register capture passed");
        Phase("reading mapped runtime package");
        std::unique_ptr<AAsset,decltype(&AAsset_close)> asset(AAssetManager_open(manager,"runtime.map",AASSET_MODE_BUFFER),AAsset_close);
        DiscoMap::Require(bool(asset),"Missing runtime package");
        off64_t length=AAsset_getLength64(asset.get());
        DiscoMap::Require(length>0 && length<=128*1024*1024,"Runtime asset exceeds bound");
        const auto* bytes=static_cast<const uint8_t*>(AAsset_getBuffer(asset.get()));
        DiscoMap::Require(bytes,"Runtime asset could not be read");
        auto* retained=new DiscoMap::Image(bytes,length);auto& image=*retained;image.Map();
        imageBase=reinterpret_cast<uintptr_t>(image.At(0));DiscoDarwin::ConfigureImage(image.At(0),image.span);DiscoDarwin::InstallCrashReport();
        Phase("image segments mapped and pointer rebases applied");
        std::set<std::string> missing;unsigned resolved=0;
        size_t guardPage=getpagesize();
        auto* unsupportedData=static_cast<uint8_t*>(mmap(nullptr,guardPage*std::size(missingNames),PROT_NONE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0));
        DiscoMap::Require(unsupportedData!=MAP_FAILED,"Unsupported-data guard allocation failed");
        for(auto& b:image.bindings) {
            const char* name=image.Name(b.name);uintptr_t address=Resolve(name);
            if(address) {DiscoMap::Require(b.addend==0,"Bridge addend unsupported");++resolved;}
            else {missing.insert(name);for(unsigned i=0;i<sizeof(missingNames)/sizeof(*missingNames);++i)if(!std::strcmp(name,missingNames[i])){address=missingCallable[i]?reinterpret_cast<uintptr_t>(missingThunks[i]):reinterpret_cast<uintptr_t>(unsupportedData+i*guardPage);DiscoMap::Require(b.addend>=0&&size_t(b.addend)<guardPage,"Unsupported import addend out of range");address+=b.addend;break;}}
            // Unknown calls stop with their symbol name; no fake success or silent fallback.
            DiscoMap::Require(address!=0,"Import has no explicit bridge or failure guard");image.Bind(b.address,address);
        }
        image.Seal();
        Phase("bindings staged and executable segments sealed RX");
        asset.release(); // Keep package backing and mapped callbacks alive until process exit.
        allocations=0;frees=0;clockQueries=0;
        struct Vector3{float x,y,z;};using Dot=float(*)(Vector3,Vector3,const void*);
        auto dot=reinterpret_cast<Dot>(image.At(RuntimePins::Dot,24,4));
        bool dotPassed=dot({1,2,3},{4,5,6},nullptr)==32 && dot({-1,2,-3},{4,-5,6},nullptr)==-32;
        Phase("original image arithmetic returned");
        auto allocate=reinterpret_cast<void*(*)(size_t)>(image.Symbol("_il2cpp_alloc"));
        auto release=reinterpret_cast<void(*)(void*)>(image.Symbol("_il2cpp_free"));
        bool allocatorPassed=true;
        for(size_t n:{size_t(1),size_t(4096),size_t(1024*1024)}) {
            void* memory=allocate(n);if(!memory){allocatorPassed=false;break;}
            std::memset(memory,0xa5,n);auto* data=static_cast<uint8_t*>(memory);
            allocatorPassed &= data[0]==0xa5 && data[n-1]==0xa5;release(memory);
        }
        allocatorPassed &= allocations==3 && frees==3;
        Phase("original IL2CPP allocator exports returned through Android bridge");
        DiscoMap::Require(!image.initializers.empty() && image.initializers[0]==RuntimePins::ClockInit,"Unexpected reviewed initializer");
        auto initializeClock=reinterpret_cast<void(*)()>(image.At(RuntimePins::ClockInit,4,4));initializeClock();
        uint64_t clockData[2];double ratio;
        std::memcpy(clockData,image.At(RuntimePins::ClockData,16,2),16);
        std::memcpy(&ratio,image.At(RuntimePins::ClockRatio,8,2),8);
        bool clockPassed=clockQueries==1 && clockData[0]==1 && clockData[1]==1 && ratio==1;
        Phase("reviewed original clock initializer returned");
        for(size_t i=1;i<image.initializers.size();++i){
            __android_log_print(ANDROID_LOG_INFO,"DiscoRuntime","running initializer %zu offset=%llx",i,(unsigned long long)image.initializers[i]);
            reinterpret_cast<void(*)()>(image.At(image.initializers[i],4,4))();
            __android_log_print(ANDROID_LOG_INFO,"DiscoRuntime","initializer %zu completed",i);
        }
        Phase("all original image initializers completed; configuring metadata path");
        reinterpret_cast<void(*)(const char*)>(image.Symbol("_il2cpp_set_data_dir"))(dataPath);
        Phase("calling original il2cpp_init");
        int initialized=reinterpret_cast<int(*)(const char*)>(image.Symbol("_il2cpp_init"))("DiscoAndroidRuntime");
        __android_log_print(ANDROID_LOG_INFO,"DiscoRuntime","il2cpp_init returned %d",initialized);
        DiscoMap::Require(initialized!=0,"Original runtime initialization returned failure");
        auto domain=reinterpret_cast<void*(*)()>(image.Symbol("_il2cpp_domain_get"))();
        DiscoMap::Require(domain,"Runtime domain missing");
        auto assembly=reinterpret_cast<void*(*)(void*,const char*)>(image.Symbol("_il2cpp_domain_assembly_open"))(domain,"UnityEngine.CoreModule.dll");
        DiscoMap::Require(assembly,"CoreModule assembly missing");
        auto module=reinterpret_cast<void*(*)(void*)>(image.Symbol("_il2cpp_assembly_get_image"))(assembly);
        auto klass=reinterpret_cast<void*(*)(void*,const char*,const char*)>(image.Symbol("_il2cpp_class_from_name"))(module,"UnityEngine","Vector3");
        DiscoMap::Require(klass,"Vector3 metadata class missing");
        auto method=reinterpret_cast<void*(*)(void*,const char*,int)>(image.Symbol("_il2cpp_class_get_method_from_name"))(klass,"Dot",2);
        DiscoMap::Require(method,"Vector3.Dot metadata method missing");
        Vector3 left{1,2,3},right{4,5,6};void* arguments[]={&left,&right};void* exception=nullptr;
        auto result=reinterpret_cast<void*(*)(void*,void*,void**,void**)>(image.Symbol("_il2cpp_runtime_invoke"))(method,nullptr,arguments,&exception);
        DiscoMap::Require(result&&!exception,"Metadata invocation failed");
        auto unboxed=reinterpret_cast<float*(*)(void*)>(image.Symbol("_il2cpp_object_unbox"))(result);
        bool invokePassed=unboxed&&*unboxed==32;
        DiscoMap::Require(invokePassed,"Metadata-invoked arithmetic mismatch");
        Phase("metadata lookup and original runtime_invoke returned expected arithmetic");
        reinterpret_cast<void(*)(int)>(image.Symbol("_il2cpp_gc_collect"))(2);
        Phase("original full garbage collection returned");
        std::ostringstream out;
        out<<"{\"included\":true,\"mapped_bytes\":"<<image.span<<",\"segments\":"<<image.segments.size()
           <<",\"rebases\":"<<image.rebases.size()<<",\"bindings_resolved\":"<<resolved
           <<",\"unresolved_import_symbols\":"<<missing.size()<<",\"executable_bytes_unchanged\":"<<(image.executableUnchanged?"true":"false")
           <<",\"dot_passed\":"<<(dotPassed?"true":"false")<<",\"allocator_passed\":"<<(allocatorPassed?"true":"false")
           <<",\"clock_initializer_passed\":"<<(clockPassed?"true":"false")
           <<",\"passed\":"<<(dotPassed&&allocatorPassed&&clockPassed&&threadPassed&&invokePassed&&initialized?"true":"false")
           <<",\"thread_bridge_passed\":true,\"metadata_invocation_passed\":true,\"gc_collection_returned\":true"
           <<",\"initializers_completed\":"<<image.initializers.size()<<",\"full_runtime_initialized\":"<<(initialized?"true":"false")<<",\"scope\":\"Original runtime startup experiment; engine and gameplay not integrated\"}";
        return out.str();
    } catch(const std::exception& error) {
        Phase(error.what());return "{\"included\":true,\"passed\":false,\"error\":\"Mapped runtime failed; see DiscoRuntime log\"}";
    }
#endif
}
