// A bounded import bridge and selected entry-point tests. Full IL2CPP boot is gated.
#include "MappedImage.h"
#include <android/asset_manager.h>
#include <android/log.h>
#include <cstdlib>
#include <ctime>
#include <sstream>
#include <memory>
#ifdef DISCO_MAPPED_RUNTIME
#include "RuntimePins.h"
#endif

namespace {
unsigned allocations=0,frees=0,clockQueries=0;
void* Allocate(size_t n){++allocations;return std::malloc(n);}
void Release(void* p){++frees;std::free(p);}
struct Timebase {uint32_t numerator,denominator;};
int TimebaseInfo(Timebase* value){++clockQueries;if(!value)return 4;value->numerator=1;value->denominator=1;return 0;}
uintptr_t Resolve(const char* symbol) {
    // Each entry is explicit. No dlsym-by-name assumption for Darwin ABI calls.
    if(!std::strcmp(symbol,"_malloc"))return reinterpret_cast<uintptr_t>(&Allocate);
    if(!std::strcmp(symbol,"_free"))return reinterpret_cast<uintptr_t>(&Release);
    if(!std::strcmp(symbol,"_mach_timebase_info"))return reinterpret_cast<uintptr_t>(&TimebaseInfo);
    return 0;
}
void Phase(const char* phase){__android_log_print(ANDROID_LOG_INFO,"DiscoRuntime","%s",phase);}
}

std::string DiscoRuntimeReport(AAssetManager* manager) {
#ifndef DISCO_MAPPED_RUNTIME
    return "{\"included\":false}";
#else
    try {
        Phase("reading mapped runtime package");
        std::unique_ptr<AAsset,decltype(&AAsset_close)> asset(AAssetManager_open(manager,"runtime.map",AASSET_MODE_BUFFER),AAsset_close);
        DiscoMap::Require(bool(asset),"Missing runtime package");
        off64_t length=AAsset_getLength64(asset.get());
        DiscoMap::Require(length>0 && length<=128*1024*1024,"Runtime asset exceeds bound");
        const auto* bytes=static_cast<const uint8_t*>(AAsset_getBuffer(asset.get()));
        DiscoMap::Require(bytes,"Runtime asset could not be read");
        DiscoMap::Image image(bytes,length);image.Map();
        Phase("image segments mapped and pointer rebases applied");
        std::set<std::string> missing;unsigned resolved=0;
        for(auto& b:image.bindings) {
            const char* name=image.Name(b.name);uintptr_t address=Resolve(name);
            if(address) {DiscoMap::Require(b.addend==0,"Bridge addend unsupported");++resolved;}
            else missing.insert(name);
            // Unknown imports stay null. Only statically reviewed entry points run.
            image.Bind(b.address,address);
        }
        image.Seal();
        Phase("bindings staged and executable segments sealed RX");
        allocations=frees=clockQueries=0;
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
        std::ostringstream out;
        out<<"{\"included\":true,\"mapped_bytes\":"<<image.span<<",\"segments\":"<<image.segments.size()
           <<",\"rebases\":"<<image.rebases.size()<<",\"bindings_resolved\":"<<resolved
           <<",\"unresolved_import_symbols\":"<<missing.size()<<",\"executable_bytes_unchanged\":"<<(image.executableUnchanged?"true":"false")
           <<",\"dot_passed\":"<<(dotPassed?"true":"false")<<",\"allocator_passed\":"<<(allocatorPassed?"true":"false")
           <<",\"clock_initializer_passed\":"<<(clockPassed?"true":"false")
           <<",\"passed\":"<<(dotPassed&&allocatorPassed&&clockPassed?"true":"false")
           <<",\"full_runtime_initialized\":false,\"scope\":\"Mapped original image and three audited imports; full ABI and runtime initialization remain unresolved\"}";
        return out.str();
    } catch(const std::exception& error) {
        Phase(error.what());return "{\"included\":true,\"passed\":false,\"error\":\"Mapped runtime failed; see DiscoRuntime log\"}";
    }
#endif
}
