// Android ELF entry points forwarding into the locally supplied ARM64 runtime.
#include "RuntimeLoader.h"
#include "AndroidLocale.h"
#include "RuntimeExports.h"
#include <android/asset_manager_jni.h>
#include <android/log.h>
#include <jni.h>
#include <mutex>
#include <string>
#include <pthread.h>
#include <ctime>
#include "il2cpp-api.h"
#include "GeneratedIcalls.h"
#include <dlfcn.h>
extern "C" void DiscoTextPopulateBridge();
extern "C" Il2CppMethodPointer DiscoTextPopulateTarget;

extern "C" {__attribute__((visibility("hidden"))) void* DiscoExportTargets[std::size(discoExportNames)]{};}
namespace {
DiscoRuntime::Module* module=nullptr;
std::string metadataRoot,gameRoot,streamingRoot;
std::mutex prepareLock;
using Invoke=Il2CppObject*(*)(const MethodInfo*,void*,void**,Il2CppException**);
Invoke originalInvoke=nullptr;
void Log(const char* value){__android_log_print(ANDROID_LOG_INFO,"DiscoUnity","%s",value);}
}
namespace {
pthread_t unityThread;
std::string DiscoAndroidSceneText(Il2CppString* text){
    std::string result;auto* chars=il2cpp_string_chars(text);int count=il2cpp_string_length(text);
    for(int i=0;i<count;++i){uint32_t c=chars[i];if(c>=0xd800&&c<=0xdbff){DiscoMap::Require(i+1<count&&chars[i+1]>=0xdc00&&chars[i+1]<=0xdfff,"Invalid UTF16 scene name");c=0x10000+((c-0xd800)<<10)+(chars[++i]-0xdc00);}else DiscoMap::Require(c<0xdc00||c>0xdfff,"Invalid UTF16 scene name");
        if(c<0x80)result+=char(c);else if(c<0x800){result+=char(0xc0|(c>>6));result+=char(0x80|(c&63));}else if(c<0x10000){result+=char(0xe0|(c>>12));result+=char(0x80|((c>>6)&63));result+=char(0x80|(c&63));}else{result+=char(0xf0|(c>>18));result+=char(0x80|((c>>12)&63));result+=char(0x80|((c>>6)&63));result+=char(0x80|(c&63));}}
    return result;
}
bool DiscoAndroidUnityThread(){return pthread_equal(unityThread,pthread_self());}
bool DiscoAndroidOwnsMethod(void* method,uintptr_t offset){return method==module->image->At(offset,4,4);}
}
#include "../UnityHost/iOS/DiscoSceneResidency.h"
#include "StartupDiagnostics.h"
#include "StencilCopy.h"
#include "GraphicsIcalls.h"
#include "AmplifyReadback.h"
#include "AmplifyDiagnostics.h"
#include "../UnityHost/iOS/DiscoGameDisplay.h"
#include "TouchControls.h"
#include "VirtualPad.h"
extern "C" JNIEXPORT void JNICALL Java_org_discoport_androidgame_GameActivity_pinch(JNIEnv*,jclass,jint phase,jdouble scale,jint first,jint second,jfloat x1,jfloat y1,jfloat x2,jfloat y2){
    DiscoAndroidTouch::Enqueue({phase,first,second,scale,x1,y1,x2,y2});
}
extern "C" JNIEXPORT jboolean JNICALL Java_org_discoport_androidgame_GameActivity_highlightAllowed(JNIEnv*,jclass){return DiscoAndroidTouch::highlightAllowed.load();}
extern "C" JNIEXPORT void JNICALL Java_org_discoport_androidgame_GameActivity_highlight(JNIEnv*,jclass,jboolean down){DiscoAndroidTouch::highlightRequested=down;}
extern "C" JNIEXPORT void JNICALL Java_org_discoport_androidgame_GameActivity_padEnabled(JNIEnv*,jclass,jboolean enabled){std::lock_guard<std::mutex> guard(DiscoAndroidPad::lock);DiscoAndroidPad::state.Enable(enabled);}
extern "C" JNIEXPORT void JNICALL Java_org_discoport_androidgame_GameActivity_padButton(JNIEnv*,jclass,jint button,jboolean down){std::lock_guard<std::mutex> guard(DiscoAndroidPad::lock);DiscoAndroidPad::state.Button(button,down);}
extern "C" JNIEXPORT void JNICALL Java_org_discoport_androidgame_GameActivity_padAxis(JNIEnv*,jclass,jint stick,jfloat x,jfloat y){std::lock_guard<std::mutex> guard(DiscoAndroidPad::lock);DiscoAndroidPad::state.Axis(stick,x,y);}
extern "C" JNIEXPORT void JNICALL Java_org_discoport_androidgame_GameActivity_prepareRuntime(JNIEnv* env,jclass,jobject manager,jstring path,jstring gamePath){
    std::lock_guard<std::mutex> lock(prepareLock);
    if(module)return;
    static jobject retainedAssets=env->NewGlobalRef(manager);
    if(!retainedAssets)std::abort();
    ConfigureAndroidLocale(env);
    try{
        const char* root=env->GetStringUTFChars(path,nullptr);if(!root)return;metadataRoot=root;env->ReleaseStringUTFChars(path,root);
        const char* game=env->GetStringUTFChars(gamePath,nullptr);if(!game)return;gameRoot=game;streamingRoot=gameRoot+"/StreamingAssets";env->ReleaseStringUTFChars(gamePath,game);
        module=&DiscoRuntime::Load(AAssetManager_fromJava(env,manager));
        originalInvoke=reinterpret_cast<Invoke>(module->image->Symbol("_il2cpp_runtime_invoke"));
        for(size_t i=0;i<std::size(discoExportNames);++i)DiscoExportTargets[i]=module->image->Symbol(discoExportNames[i]);
        DiscoRuntime::Initialize(*module);
        reinterpret_cast<void(*)(const char*)>(module->image->Symbol("_il2cpp_set_data_dir"))(metadataRoot.c_str());
        Log("Original ARM64 provider ready for Unity Android");
    }catch(const std::exception& error){__android_log_print(ANDROID_LOG_FATAL,"DiscoUnity","Provider preparation failed: %s",error.what());std::abort();}
}
extern "C" void il2cpp_set_data_dir(const char*){
    if(!module)std::abort();
    reinterpret_cast<void(*)(const char*)>(module->image->Symbol("_il2cpp_set_data_dir"))(metadataRoot.c_str());
}
extern "C" int il2cpp_init(const char* name){
    if(!module)std::abort();Log("Unity requested original il2cpp_init");
    int result=reinterpret_cast<int(*)(const char*)>(module->image->Symbol("_il2cpp_init"))(name);
    __android_log_print(ANDROID_LOG_INFO,"DiscoUnity","Unity runtime initialization returned %d",result);if(result){unityThread=pthread_self();DiscoSceneResidency::Install();DiscoStartup::Install();}return result;
}

namespace {
void* GameDataPath(){return reinterpret_cast<void*(*)(const char*)>(module->image->Symbol("_il2cpp_string_new"))(gameRoot.c_str());}
void* StreamingAssetsPath(){return reinterpret_cast<void*(*)(const char*)>(module->image->Symbol("_il2cpp_string_new"))(streamingRoot.c_str());}
}
extern "C" void il2cpp_add_internal_call(const char* name,Il2CppMethodPointer function){
    if(!module)std::abort();
    DiscoGraphics::Register(name,function);
    for(size_t i=0;i<std::size(discoIcalls);++i){
        const auto& entry=discoIcalls[i];const char* match=std::strstr(name,entry.suffix);
        if(!match||!(match[std::strlen(entry.suffix)]=='\0'||match[std::strlen(entry.suffix)]=='('))continue;
        Dl_info info{};
        if(!dladdr(reinterpret_cast<void*>(function),&info)||!info.dli_fname||
           !std::strstr(info.dli_fname,"libunity.so")||reinterpret_cast<uintptr_t>(function)-reinterpret_cast<uintptr_t>(info.dli_fbase)!=entry.offset)
            DiscoSceneResidency::Fail("internal-call bridge target differs from pinned engine");
        DiscoIcallTargets[i]=reinterpret_cast<void*>(function);function=entry.bridge;
        __android_log_print(ANDROID_LOG_INFO,"DiscoUnity","ABI bridge registered %s",entry.suffix);
    }
    if(!std::strcmp(name,"UnityEngine.Application::get_dataPath"))function=reinterpret_cast<Il2CppMethodPointer>(&GameDataPath);
    if(!std::strcmp(name,"UnityEngine.Application::get_streamingAssetsPath"))function=reinterpret_cast<Il2CppMethodPointer>(&StreamingAssetsPath);
    const char* textCall="UnityEngine.TextGenerator::Populate_Internal_Injected";
    size_t textLength=std::strlen(textCall);
    if(!std::strncmp(name,textCall,textLength)&&(name[textLength]=='\0'||name[textLength]=='(')){
        DiscoTextPopulateTarget=function;function=&DiscoTextPopulateBridge;
        Log("TextGenerator stack-argument bridge registered");
    }
    reinterpret_cast<void(*)(const char*,Il2CppMethodPointer)>(module->image->Symbol("_il2cpp_add_internal_call"))(name,function);
}

extern "C" Il2CppObject* il2cpp_runtime_invoke(const MethodInfo* method,void* owner,void** args,Il2CppException** error){
    if(!module)std::abort();
    static std::atomic<unsigned> diagnosticCalls{0};unsigned call=diagnosticCalls.fetch_add(1);
    if(call<12)__android_log_print(ANDROID_LOG_INFO,"DiscoUnity","Invoke begin %u %s",call,method?method->name:"<null>");
    bool inputUpdate=method&&DiscoAndroidUnityThread()&&!std::strcmp(method->name,"Update")&&
        !std::strcmp(il2cpp_class_get_name(method->klass),"InControlManager")&&
        !std::strcmp(il2cpp_class_get_namespace(method->klass),"InControl");
    if(inputUpdate)DiscoAndroidPad::Prepare();
    auto* result=originalInvoke(method,owner,args,error);
    if(inputUpdate)DiscoAndroidTouch::ApplyHighlight();
    if(method&&DiscoAndroidUnityThread()&&!std::strcmp(method->name,"OnEnable")&&
       !std::strcmp(il2cpp_class_get_name(method->klass),"OutlineLayer"))DiscoStencil::AfterOutlineEnable();
    if(method&&DiscoAndroidUnityThread()&&!std::strcmp(method->name,"Update")){
        static int previousFrame=-1;
        int frame=DiscoStencil::Icall<int(*)()>("UnityEngine.Time::get_frameCount")();
        if(frame==previousFrame)return result;
        previousFrame=frame;
        DiscoAndroidTouch::Tick();
        DiscoStencil::Pump();
        DiscoGraphics::DiagnoseInput();
        DiscoAmplifyDiagnostics::SaveCapture();
        static time_t previousRefresh=0;time_t now=std::time(nullptr);
        if(now!=previousRefresh){previousRefresh=now;DiscoGameDisplay::Refresh();DiscoGraphics::DiagnoseShaders();DiscoGraphics::DiagnoseScene();DiscoGraphics::DiagnoseSprites();DiscoAmplifyDiagnostics::Tick();}
    }
    if(call<12)__android_log_print(ANDROID_LOG_INFO,"DiscoUnity","Invoke end %u",call);
    if(owner&&method&&DiscoAndroidUnityThread()&&!std::strcmp(method->name,"Update")&&
       !std::strcmp(il2cpp_class_get_name(method->klass),"PreInitialize")){
        static time_t previous=0;time_t now=std::time(nullptr);
        if(now-previous>=10){previous=now;void* cursor=nullptr;
            while(auto* field=il2cpp_class_get_fields(method->klass,&cursor)){
                if(il2cpp_field_get_flags(field)&0x10)continue;
                int type=il2cpp_type_get_type(il2cpp_field_get_type(field));
                if(type==IL2CPP_TYPE_BOOLEAN){bool value=false;il2cpp_field_get_value(static_cast<Il2CppObject*>(owner),field,&value);__android_log_print(ANDROID_LOG_INFO,"DiscoUnity","Startup %s=%d",il2cpp_field_get_name(field),int(value));}
                else if(type==IL2CPP_TYPE_R4){float value=0;il2cpp_field_get_value(static_cast<Il2CppObject*>(owner),field,&value);__android_log_print(ANDROID_LOG_INFO,"DiscoUnity","Startup %s=%g",il2cpp_field_get_name(field),double(value));}
            }
        }
    }
    return result;
}
