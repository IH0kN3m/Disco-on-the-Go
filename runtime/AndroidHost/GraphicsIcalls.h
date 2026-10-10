// Unity 2020.3 Android display adaptation and bounded graphics diagnostics.
#pragma once
#include <algorithm>
#include <unwind.h>
#include "GraphicsFormatPolicy.h"
#include "AmplifyCoordinates.h"
namespace DiscoGraphics {
static int (*graphicsDeviceType)();
__attribute__((noinline)) static int GraphicsDeviceType() {
    uintptr_t caller=reinterpret_cast<uintptr_t>(__builtin_return_address(0));
    uintptr_t base=reinterpret_cast<uintptr_t>(module->image->At(0,1,1));
    int actual=graphicsDeviceType();
    int adapted=DiscoAmplifyCoordinates::DeviceType(actual,caller-base);
    if(adapted!=actual){
        static unsigned reports=0;if(reports++<2)DiscoSceneResidency::Log("Amplify GLES framebuffer origin adapted at %llx\n",(unsigned long long)(caller-base));
    }
    return adapted;
}
struct Resolution { int32_t width, height, refresh; };
static_assert(sizeof(Resolution)==12);
static void (*currentResolution)(Resolution*);
static void* (*resolutions)();
static void (*setResolution)(int,int,int,int);
static void CurrentResolution(Resolution* value) {
    currentResolution(value);
    if(value->width<value->height)std::swap(value->width,value->height);
}
static void* Resolutions() {
    auto* array=static_cast<Il2CppArraySize*>(resolutions());
    if(!array||array->max_length>128||il2cpp_array_element_size(il2cpp_object_get_class(reinterpret_cast<Il2CppObject*>(array)))!=sizeof(Resolution))
        DiscoSceneResidency::Fail("resolution array layout differs");
    auto* values=reinterpret_cast<Resolution*>(array->vector);
    for(size_t i=0;i<array->max_length;++i)if(values[i].width<values[i].height)std::swap(values[i].width,values[i].height);
    return array;
}
static void SetResolution(int width,int height,int mode,int refresh) {
    if(width<height)std::swap(width,height);
    setResolution(width,height,mode,refresh);
}
struct Descriptor { int32_t width,height,samples,volume,mips,color,stencil,depth,dimension,shadow,vr,flags,memoryless; };
static_assert(sizeof(Descriptor)==52);
static void (*setDescriptor)(void*,const Descriptor*);
static void* (*getTemporary)(const Descriptor*);
static bool (*isFormatSupported)(int,int);
static void (*setStencil)(void*,int);
static void (*setCameraTarget)(void*,void*);
static void (*setGlobalTarget)(int,void*,int);
static void SetCameraTarget(void* camera,void* target) {
    DiscoStencil::Detach(camera,target);
    setCameraTarget(camera,target);if(target)DiscoStencil::Attach(camera,target);
}
static void SetGlobalTarget(int property,void* target,int element) {
    if(!DiscoStencil::Bind(property,target,element))setGlobalTarget(property,target,element);
}
static void (*setColor)(void*,int);
static int CompatibleColor(int value) {
    static bool checked=false;
    if(!checked){
        auto* klass=DiscoSceneResidency::Class("UnityEngine.CoreModule.dll","UnityEngine.Experimental.Rendering","GraphicsFormat");
        for(auto pair:{std::pair<const char*,int>{"R16_UNorm",21},{"R16G16_UNorm",22},{"R32_SFloat",49},{"R32G32_SFloat",50}}){
            auto* field=il2cpp_class_get_field_from_name(klass,pair.first);int actual=-1;
            if(!field)DiscoSceneResidency::Fail("graphics format enum missing");
            il2cpp_field_static_get_value(field,&actual);
            if(actual!=pair.second)DiscoSceneResidency::Fail("graphics format enum differs");
        }
        checked=true;
    }
    return DiscoGraphicsFormat::Compatible(value,isFormatSupported);
}
static void SetColor(void* owner,int value) { setColor(owner,CompatibleColor(value)); }
static void Frame(const Il2CppStackFrameInfo* frame,void*) {
    if(frame->method)__android_log_print(ANDROID_LOG_INFO,"DiscoGraphics","  %s::%s",
        il2cpp_class_get_name(frame->method->klass),frame->method->name);
}
static void Trace(const char* operation,int format) {
    static unsigned traces=0;if(traces++>=12)return;
    __android_log_print(ANDROID_LOG_INFO,"DiscoGraphics","%s format=%d",operation,format);
    il2cpp_current_thread_walk_frame_stack(Frame,nullptr);
    unsigned frames=0;
    _Unwind_Backtrace([](_Unwind_Context* context,void* data){
        auto& n=*static_cast<unsigned*>(data);if(n++>=16)return _URC_END_OF_STACK;
        uintptr_t address=_Unwind_GetIP(context),base=reinterpret_cast<uintptr_t>(module->image->At(0,1,1));
        __android_log_print(ANDROID_LOG_INFO,"DiscoGraphics","  native %llx",static_cast<unsigned long long>(address-base));
        return _URC_NO_REASON;
    },&frames);
}
static void SetDescriptor(void* owner,const Descriptor* value) {
    if(value->color==21||value->color==22||value->stencil)Trace("descriptor",value->color);
    Descriptor adapted=*value;adapted.color=CompatibleColor(adapted.color);
    setDescriptor(owner,&adapted);
}
static void* GetTemporary(const Descriptor* value) {
    if(value->color==21||value->color==22||value->stencil)Trace("temporary",value->color);
    Descriptor adapted=*value;adapted.color=CompatibleColor(adapted.color);
    return getTemporary(&adapted);
}
static bool IsFormatSupported(int format,int usage) {
    bool result=isFormatSupported(format,usage);
    if(!result&&(format==22||format==13))Trace("unsupported format",format);
    if(!result&&(format==21||format==22)&&usage==4)return CompatibleColor(format)!=format;
    return result;
}
static void SetStencil(void* owner,int value) {
    if(value)Trace("stencil",value);
    setStencil(owner,DiscoStencil::Request(owner,value)?0:value);
}
static bool Named(const char* name,const char* expected) {
    size_t n=std::strlen(expected);return !std::strncmp(name,expected,n)&&(name[n]=='\0'||name[n]=='(');
}
static void DiagnoseShaders() {
    using namespace DiscoSceneResidency;
    static unsigned ticks=0;if(++ticks!=12)return;
    auto* shaders=Class("UnityEngine.CoreModule.dll","UnityEngine","Shader");
    for(const char* name:{"Hidden/VideoDecodeAndroid","Hidden/VideoDecode","UI/Default","Hidden/OutlineColor"}){
        auto* text=il2cpp_string_new(name);void* args[]={text};auto* shader=Call(shaders,"Find",1,nullptr,args);
        DiscoSceneResidency::Log("Shader lookup %s found=%d\n",name,shader!=nullptr);
    }
    auto* resources=Class("UnityEngine.CoreModule.dll","UnityEngine","Resources");
    void* args[]={il2cpp_type_get_object(il2cpp_class_get_type(shaders))};
    auto* array=reinterpret_cast<Il2CppArraySize*>(Call(resources,"FindObjectsOfTypeAll",1,nullptr,args));
    if(!array||array->max_length>4096)Fail("shader inventory size");
    DiscoSceneResidency::Log("Loaded shader objects=%llu\n",(unsigned long long)array->max_length);
    auto** values=reinterpret_cast<Il2CppObject**>(array->vector);
    auto* objects=Class("UnityEngine.CoreModule.dll","UnityEngine","Object");
    for(size_t i=0;i<array->max_length;++i){
        auto name=Text(reinterpret_cast<Il2CppString*>(Call(objects,"get_name",0,values[i],nullptr)));
        if(name.find("Video")!=std::string::npos)DiscoSceneResidency::Log("Loaded video shader %s\n",name.c_str());
    }
}
static void DiagnoseScene() {
    using namespace DiscoSceneResidency;
    static unsigned ticks=0;if(++ticks!=30&&ticks!=90)return;
    auto* resources=Class("UnityEngine.CoreModule.dll","UnityEngine","Resources");
    auto* objects=Class("UnityEngine.CoreModule.dll","UnityEngine","Object");
    auto* components=Class("UnityEngine.CoreModule.dll","UnityEngine","Component");
    auto* behaviour=Class("UnityEngine.CoreModule.dll","UnityEngine","Behaviour");
    auto* go=Class("UnityEngine.CoreModule.dll","UnityEngine","GameObject");
    for(const char* kind:{"Camera","Canvas"}) {
        auto* type=Class(kind[0]=='C'&&kind[1]=='a'&&kind[2]=='m'?"UnityEngine.CoreModule.dll":"UnityEngine.UIModule.dll","UnityEngine",kind);
        void* args[]={il2cpp_type_get_object(il2cpp_class_get_type(type))};
        auto* array=reinterpret_cast<Il2CppArraySize*>(Call(resources,"FindObjectsOfTypeAll",1,nullptr,args));
        if(!array||array->max_length>4096)Fail("render inventory size");
        Log("Render inventory %s count=%llu\n",kind,(unsigned long long)array->max_length);
        auto** values=reinterpret_cast<Il2CppObject**>(array->vector);
        for(size_t i=0;i<std::min<size_t>(array->max_length,64);++i) {
            auto* owner=values[i];
            auto name=Text(reinterpret_cast<Il2CppString*>(Call(objects,"get_name",0,owner,nullptr)));
            auto* game=Call(components,"get_gameObject",0,owner,nullptr);
            bool active=Boolean(Call(go,"get_activeInHierarchy",0,game,nullptr));
            bool enabled=Boolean(Call(behaviour,"get_enabled",0,owner,nullptr));
            Log("Render %s %s active=%d enabled=%d\n",kind,name.c_str(),active,enabled);
            if(kind[2]=='m') {
                auto* target=Call(type,"get_targetTexture",0,owner,nullptr);
                Log("Camera %s target=%p mask=%x clear=%d\n",name.c_str(),target,
                    Integer(Call(type,"get_cullingMask",0,owner,nullptr)),Integer(Call(type,"get_clearFlags",0,owner,nullptr)));
            } else Log("Canvas %s mode=%d\n",name.c_str(),Integer(Call(type,"get_renderMode",0,owner,nullptr)));
        }
    }
}
static void DiagnoseInput() {
    static unsigned count=0;if(count>=16)return;
    auto down=DiscoStencil::Icall<bool(*)(int)>("UnityEngine.Input::GetMouseButtonDown");
    if(!down(0))return;
    struct Position {float x,y,z;} position;
    DiscoStencil::Icall<void(*)(Position*)>("UnityEngine.Input::get_mousePosition_Injected")(&position);
    DiscoSceneResidency::Log("Android pointer down x=%.1f y=%.1f z=%.1f\n",position.x,position.y,position.z);++count;
}
static void DiagnoseSprites() {
    using namespace DiscoSceneResidency;
    static unsigned ticks=0;if(++ticks!=30&&ticks!=90)return;
    auto* resources=Class("UnityEngine.CoreModule.dll","UnityEngine","Resources");
    auto* image=Class("UnityEngine.UI.dll","UnityEngine.UI","Image");
    auto* objects=Class("UnityEngine.CoreModule.dll","UnityEngine","Object");
    auto* components=Class("UnityEngine.CoreModule.dll","UnityEngine","Component");
    auto* gameObjects=Class("UnityEngine.CoreModule.dll","UnityEngine","GameObject");
    auto* textures=Class("UnityEngine.CoreModule.dll","UnityEngine","Texture");
    auto* utility=Class("UnityEngine.CoreModule.dll","UnityEngine.Sprites","DataUtility");
    void* args[]={il2cpp_type_get_object(il2cpp_class_get_type(image))};
    auto* array=reinterpret_cast<Il2CppArraySize*>(Call(resources,"FindObjectsOfTypeAll",1,nullptr,args));
    if(!array||array->max_length>16384)Fail("sprite inventory bounds");
    auto** values=reinterpret_cast<Il2CppObject**>(array->vector);unsigned reported=0;
    for(size_t i=0;i<array->max_length&&reported<40;++i){
        auto* owner=values[i];auto* go=Call(components,"get_gameObject",0,owner,nullptr);
        if(!Boolean(Call(gameObjects,"get_activeInHierarchy",0,go,nullptr)))continue;
        auto* sprite=Call(image,"get_overrideSprite",0,owner,nullptr);if(!sprite)continue;
        auto* texture=Call(image,"get_mainTexture",0,owner,nullptr);if(!texture)continue;
        void* uvArgs[]={sprite};auto* uv=Call(utility,"GetOuterUV",1,nullptr,uvArgs);
        uint32_t alignment=0;
        if(!uv||il2cpp_class_value_size(il2cpp_object_get_class(uv),&alignment)!=16)Fail("sprite UV layout");
        auto* data=static_cast<float*>(il2cpp_object_unbox(uv));
        auto name=Text(reinterpret_cast<Il2CppString*>(Call(objects,"get_name",0,owner,nullptr)));
        Log("Sprite image=%s texture=%dx%d uv=%.6f,%.6f,%.6f,%.6f\n",name.c_str(),
            Integer(Call(textures,"get_width",0,texture,nullptr)),Integer(Call(textures,"get_height",0,texture,nullptr)),
            data[0],data[1],data[2],data[3]);++reported;
    }
}
template<class F> static bool Bind(const char* name,const char* expected,Il2CppMethodPointer& function,F& target,F adapter) {
    if(!Named(name,expected))return false;
    target=reinterpret_cast<F>(function);function=reinterpret_cast<Il2CppMethodPointer>(adapter);return true;
}
static void Register(const char* name,Il2CppMethodPointer& function) {
    if(Bind(name,"UnityEngine.SystemInfo::GetGraphicsDeviceType",function,graphicsDeviceType,GraphicsDeviceType))
        DiscoSceneResidency::Log("Amplify graphics-device coordinate adapter registered\n");
    Bind(name,"UnityEngine.Screen::get_currentResolution_Injected",function,currentResolution,CurrentResolution);
    Bind(name,"UnityEngine.Screen::get_resolutions",function,resolutions,Resolutions);
    Bind(name,"UnityEngine.Screen::SetResolution",function,setResolution,SetResolution);
    Bind(name,"UnityEngine.RenderTexture::SetRenderTextureDescriptor_Injected",function,setDescriptor,SetDescriptor);
    Bind(name,"UnityEngine.RenderTexture::GetTemporary_Internal_Injected",function,getTemporary,GetTemporary);
    Bind(name,"UnityEngine.RenderTexture::set_stencilFormat",function,setStencil,SetStencil);
    Bind(name,"UnityEngine.Camera::set_targetTexture",function,setCameraTarget,SetCameraTarget);
    Bind(name,"UnityEngine.Shader::SetGlobalRenderTextureImpl",function,setGlobalTarget,SetGlobalTarget);
    Bind(name,"UnityEngine.RenderTexture::set_graphicsFormat",function,setColor,SetColor);
    Bind(name,"UnityEngine.SystemInfo::IsFormatSupported",function,isFormatSupported,IsFormatSupported);
}
}
