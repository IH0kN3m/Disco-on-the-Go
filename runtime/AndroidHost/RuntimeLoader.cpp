// Original runtime mapper shared by the diagnostic and the Android Unity provider.
#include "RuntimeLoader.h"
#include "DarwinBridge.h"
#include <android/log.h>
#include <memory>
#include <sys/auxv.h>
#include <asm/hwcap.h>
#ifdef DISCO_MAPPED_RUNTIME
#include "MissingImports.h"
#include "AmplifyReadback.h"
#endif
namespace DiscoDarwin {uintptr_t ResolveAdditional(const char*);void ConfigureImage(void*,size_t);void InstallCrashReport();}
#ifdef DISCO_MAPPED_RUNTIME
static uintptr_t imageBase=0;
extern "C" [[noreturn]] void DiscoUnsupportedTrap(unsigned n,uintptr_t caller){__android_log_print(ANDROID_LOG_FATAL,"DiscoRuntime","UNSUPPORTED IMPORT %s caller_image_offset=%llx",n<sizeof(missingNames)/sizeof(*missingNames)?missingNames[n]:"invalid",(unsigned long long)(caller-imageBase));std::abort();}
#endif
namespace DiscoRuntime {
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

#ifdef DISCO_MAPPED_RUNTIME
namespace DiscoRuntime {
void RegisterUnwind(AAssetManager*,DiscoMap::Image&,const char*);
static AAssetManager* assetManager=nullptr;
static Module* amplify=nullptr;
Module* LoadImage(AAssetManager* manager,const char* package,const char* unwind,bool mainImage){
        if(mainImage){
            unsigned long features=getauxval(AT_HWCAP);
            // The pinned executable contains LSE atomics and UDOT. Its three
            // SHA3 EOR3 uses are translated during private package staging.
            DiscoMap::Require((features&(HWCAP_ATOMICS|HWCAP_ASIMDDP))==(HWCAP_ATOMICS|HWCAP_ASIMDDP),
                "Original runtime requires ARM64 LSE atomics and SIMD dot-product support");
        }
        Phase("reading mapped runtime package");
        std::unique_ptr<AAsset,decltype(&AAsset_close)> asset(AAssetManager_open(manager,package,AASSET_MODE_BUFFER),AAsset_close);
        DiscoMap::Require(bool(asset),"Missing runtime package");
        off64_t length=AAsset_getLength64(asset.get());
        DiscoMap::Require(length>0 && length<=128*1024*1024,"Runtime asset exceeds bound");
        const auto* bytes=static_cast<const uint8_t*>(AAsset_getBuffer(asset.get()));
        DiscoMap::Require(bytes,"Runtime asset could not be read");
        auto* retained=new DiscoMap::Image(bytes,length);auto& image=*retained;image.Map();
        if(mainImage){imageBase=reinterpret_cast<uintptr_t>(image.At(0));DiscoDarwin::ConfigureImage(image.At(0),image.span);DiscoDarwin::InstallCrashReport();}
        Phase("image segments mapped and pointer rebases applied");
        std::set<std::string> missing;unsigned resolved=0;
        size_t guardPage=getpagesize();
        auto* unsupportedData=static_cast<uint8_t*>(mmap(nullptr,guardPage*std::size(missingNames),PROT_NONE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0));
        DiscoMap::Require(unsupportedData!=MAP_FAILED,"Unsupported-data guard allocation failed");
        for(auto& b:image.bindings) {
            const char* name=image.Name(b.name);uintptr_t address=Resolve(name);
            if(address) {DiscoMap::Require(b.addend==0||(b.addend==16&&!std::strncmp(name,"__ZTVN10__cxxabiv1",16)),"Bridge addend unsupported");address+=b.addend;++resolved;}
            else {missing.insert(name);for(unsigned i=0;i<sizeof(missingNames)/sizeof(*missingNames);++i)if(!std::strcmp(name,missingNames[i])){address=missingCallable[i]?reinterpret_cast<uintptr_t>(missingThunks[i]):reinterpret_cast<uintptr_t>(unsupportedData+i*guardPage);DiscoMap::Require(b.addend>=0&&size_t(b.addend)<guardPage,"Unsupported import addend out of range");address+=b.addend;break;}}
            // Unknown calls stop with their symbol name; no fake success or silent fallback.
            DiscoMap::Require(address!=0,"Import has no explicit bridge or failure guard");image.Bind(b.address,address);
        }
        image.Seal();
        RegisterUnwind(manager,image,unwind);
        Phase("bindings staged and executable segments sealed RX");
        asset.release(); // Keep package backing and mapped callbacks alive until process exit.
    return new Module{retained,resolved,missing.size()};
}
Module& Load(AAssetManager* manager){
    static std::mutex lock;static Module* loaded=nullptr;
    std::lock_guard<std::mutex> guard(lock);
    if(!loaded){assetManager=manager;loaded=LoadImage(manager,"runtime.map","unwind.map",true);}return *loaded;
}
void* TryOpenPlugin(const char* path){
    if(!path)return nullptr;
    std::string name=path;auto slash=name.find_last_of('/');if(slash!=std::string::npos)name=name.substr(slash+1);
    if(name!="AmplifyTextureNative"&&name!="libAmplifyTextureNative.so"&&name!="AmplifyTextureNative.bundle"&&name!="AmplifyTextureNative.dylib")return nullptr;
    static std::mutex lock;std::lock_guard<std::mutex> guard(lock);
    if(!amplify){DiscoMap::Require(assetManager,"Plugin requested before runtime");amplify=LoadImage(assetManager,"amplify.map","amplify-unwind.map",false);Initialize(*amplify);Phase("Original Amplify CPU plugin mapped and initialized");}
    return amplify;
}
bool PluginHandle(void* handle){return amplify&&handle==amplify;}
void* PluginSymbol(void* handle,const char* symbol){
    if(!PluginHandle(handle)||!symbol)return nullptr;std::string name="_";name+=symbol;
    if(void* adapter=DiscoAmplifyReadback::Symbol(symbol))return adapter;
    for(auto& exported:amplify->image->exports)if(name==amplify->image->Name(exported.name))return amplify->image->At(exported.address);
    return nullptr;
}
void Initialize(Module& module){
    if(module.initialized)return;
    for(auto address:module.image->initializers)reinterpret_cast<void(*)()>(module.image->At(address,4,4))();
    module.initialized=true;Phase("original mapped image initializers completed");
}
}
#endif
