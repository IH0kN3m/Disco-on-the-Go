// Explicit native startup experiment, followed by metadata invocation and GC checks.
#include "RuntimeLoader.h"
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
extern "C" __attribute__((returns_twice)) int DiscoPluginSetjmp(void*);
extern "C" [[noreturn]] void DiscoPluginLongjmp(void*,int);
namespace DiscoRuntime {void* TryOpenPlugin(const char*);void* PluginSymbol(void*,const char*);}
static bool JumpSelfTest(){
    alignas(16) uint8_t state[208]{};std::memset(state+192,0xa5,16);
    volatile int phase=0;int value=DiscoPluginSetjmp(state);
    if(!value){phase=1;DiscoPluginLongjmp(state,7);}
    if(value!=7||phase!=1)return false;
    for(unsigned i=192;i<208;++i)if(state[i]!=0xa5)return false;
    value=DiscoPluginSetjmp(state);if(!value&&phase==1){phase=2;DiscoPluginLongjmp(state,0);}
    return value==1&&phase==2;
}
using namespace DiscoRuntime;
bool DiscoIcallSelfTest();

std::string DiscoRuntimeReport(AAssetManager* manager,const char* dataPath) {
#ifndef DISCO_MAPPED_RUNTIME
    return "{\"included\":false}";
#else
    try {
        DiscoMap::Require(DiscoIcallSelfTest(),"Apple-to-Android text stack ABI check failed");
        Phase("Text internal-call bridge preserves mixed register/stack arguments and output guards");
        DiscoMap::Require(JumpSelfTest(),"Plugin nonlocal jump check failed");
        Phase("Plugin setjmp/longjmp restored execution and protected buffer bounds");
        bool threadPassed=DiscoDarwin::ThreadBridgeSelfTest();
        DiscoMap::Require(threadPassed,"Collector thread bridge self-test failed");
        Phase("synthetic thread suspension/resume and register capture passed");
        auto& loadedModule=DiscoRuntime::Load(manager);auto& image=*loadedModule.image;
        auto resolved=loadedModule.resolved;auto missingCount=loadedModule.missing;
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
        auto core=reinterpret_cast<void*(*)(void*,const char*)>(image.Symbol("_il2cpp_domain_assembly_open"))(domain,"mscorlib.dll");
        auto coreImage=reinterpret_cast<void*(*)(void*)>(image.Symbol("_il2cpp_assembly_get_image"))(core);
        auto integerClass=reinterpret_cast<void*(*)(void*,const char*,const char*)>(image.Symbol("_il2cpp_class_from_name"))(coreImage,"System","Int32");
        auto parse=reinterpret_cast<void*(*)(void*,const char*,int)>(image.Symbol("_il2cpp_class_get_method_from_name"))(integerClass,"Parse",1);
        DiscoMap::Require(parse,"Int32.Parse metadata missing");
        auto input=reinterpret_cast<void*(*)(const char*)>(image.Symbol("_il2cpp_string_new"))("invalid-number");void* parseArgs[]={input};exception=nullptr;
        reinterpret_cast<void*(*)(void*,void*,void**,void**)>(image.Symbol("_il2cpp_runtime_invoke"))(parse,nullptr,parseArgs,&exception);
        DiscoMap::Require(exception,"Expected managed parse exception was not returned");
        auto exceptionClass=reinterpret_cast<void*(*)(void*)>(image.Symbol("_il2cpp_object_get_class"))(exception);
        auto exceptionName=reinterpret_cast<const char*(*)(void*)>(image.Symbol("_il2cpp_class_get_name"))(exceptionClass);
        DiscoMap::Require(!std::strcmp(exceptionName,"FormatException"),"Unexpected managed exception type");
        Phase("original managed exception unwound and was caught by runtime_invoke");
        auto zoneClass=reinterpret_cast<void*(*)(void*,const char*,const char*)>(image.Symbol("_il2cpp_class_from_name"))(coreImage,"System","TimeZoneInfo");
        auto localZone=reinterpret_cast<void*(*)(void*,const char*,int)>(image.Symbol("_il2cpp_class_get_method_from_name"))(zoneClass,"get_Local",0);
        exception=nullptr;auto zone=reinterpret_cast<void*(*)(void*,void*,void**,void**)>(image.Symbol("_il2cpp_runtime_invoke"))(localZone,nullptr,nullptr,&exception);
        DiscoMap::Require(zone&&!exception,"Managed Android timezone lookup failed");
        Phase("Original managed timezone lookup completed against Android tzdata");
        reinterpret_cast<void(*)(int)>(image.Symbol("_il2cpp_gc_collect"))(2);
        Phase("original full garbage collection returned");
        void* plugin=TryOpenPlugin("AmplifyTextureNative");DiscoMap::Require(plugin,"Amplify provider missing");
        auto create=reinterpret_cast<void*(*)(int,const uint8_t*,int)>(PluginSymbol(plugin,"CreatePageDecoder"));
        auto decode=reinterpret_cast<int(*)(void*,const uint8_t*,uint8_t*)>(PluginSymbol(plugin,"DecodeBC1ToRGBX"));
        auto destroy=reinterpret_cast<void(*)(void*)>(PluginSymbol(plugin,"DestroyPageDecoder"));
        DiscoMap::Require(create&&decode&&destroy,"Amplify CPU API missing");
        const uint8_t plane[]={1,0,100},block[]={0,248,0,0,0,0,0,0};uint8_t pixels[64]{};
        void* decoder=create(4,plane,1);DiscoMap::Require(decoder,"Amplify decoder construction failed");
        int decoded=decode(decoder,block,pixels);destroy(decoder);DiscoMap::Require(decoded==0,"Amplify BC1 decode failed");
        for(unsigned i=0;i<16;++i)DiscoMap::Require(pixels[i*4]==255&&pixels[i*4+1]==0&&pixels[i*4+2]==0,"Amplify decoded pixels differ");
        Phase("Original Amplify CPU plugin decoded BC1 reference pixels");
        std::ostringstream out;
        out<<"{\"included\":true,\"mapped_bytes\":"<<image.span<<",\"segments\":"<<image.segments.size()
           <<",\"rebases\":"<<image.rebases.size()<<",\"bindings_resolved\":"<<resolved
           <<",\"unresolved_import_symbols\":"<<missingCount<<",\"executable_bytes_unchanged\":"<<(image.executableUnchanged?"true":"false")
           <<",\"dot_passed\":"<<(dotPassed?"true":"false")<<",\"allocator_passed\":"<<(allocatorPassed?"true":"false")
           <<",\"clock_initializer_passed\":"<<(clockPassed?"true":"false")
           <<",\"passed\":"<<(dotPassed&&allocatorPassed&&clockPassed&&threadPassed&&invokePassed&&initialized?"true":"false")
           <<",\"thread_bridge_passed\":true,\"metadata_invocation_passed\":true,\"managed_exception_passed\":true,\"gc_collection_returned\":true"
           <<",\"timezone_passed\":true,\"plugin_bc1_passed\":true,\"nonlocal_jump_passed\":true"
           <<",\"initializers_completed\":"<<image.initializers.size()<<",\"full_runtime_initialized\":"<<(initialized?"true":"false")<<",\"scope\":\"Original runtime startup experiment; engine and gameplay not integrated\"}";
        return out.str();
    } catch(const std::exception& error) {
        Phase(error.what());return "{\"included\":true,\"passed\":false,\"error\":\"Mapped runtime failed; see DiscoRuntime log\"}";
    }
#endif
}
