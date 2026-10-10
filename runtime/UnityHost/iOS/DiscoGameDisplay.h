// Original display adapter using the supplied game's existing aspect helpers.
#pragma once
#include "DisplayProfile.h"
namespace DiscoGameDisplay {
using namespace DiscoSceneResidency;
static const MethodInfo* Method(Il2CppClass* klass, const char* name, int count, uintptr_t address, bool isStatic = true) {
    const MethodInfo* method = il2cpp_class_get_method_from_name(klass, name, count);
#ifdef __ANDROID__
    if (!method || bool(method->flags & 0x10) != isStatic || !DiscoAndroidOwnsMethod((void*)method->methodPointer,address))
        Fail("game display method differs from inspected reference");
#else
    Dl_info image = {};
    if (!method || bool(method->flags & 0x10) != isStatic || !dladdr((void*)method->methodPointer, &image) ||
        !image.dli_fname || !strstr(image.dli_fname, "/GameAssembly.framework/GameAssembly") ||
        (uintptr_t)method->methodPointer - (uintptr_t)image.dli_fbase != address)
        Fail("game display method differs from inspected reference");
#endif
    return method;
}
#ifndef __ANDROID__
struct Vector2 {float x,y;};
static Vector2 VectorValue(Il2CppObject* object) {
    uint32_t alignment=0;
    if(!object||std::strcmp(il2cpp_class_get_name(il2cpp_object_get_class(object)),"Vector2")||
       il2cpp_class_value_size(il2cpp_object_get_class(object),&alignment)!=sizeof(Vector2))Fail("display Vector2 ABI");
    Vector2 value;std::memcpy(&value,il2cpp_object_unbox(object),sizeof(value));return value;
}
static DiscoDisplay::LayoutOwners LayoutOwners(Il2CppClass* fitters,Il2CppObject* root,bool& matches,const DiscoDisplay::Profile& profile) {
    auto* registryField=Field(fitters,"registry",0);
    if(!(il2cpp_field_get_flags(registryField)&0x10))Fail("display registry ownership");
    Il2CppObject* registry=nullptr;il2cpp_field_static_get_value(registryField,&registry);
    int32_t version=0;
    if(registry){
        auto* list=il2cpp_object_get_class(registry);
        auto* field=il2cpp_class_get_field_from_name(list,"_version");
        if(!field||(il2cpp_field_get_flags(field)&0x10)||il2cpp_type_get_type(il2cpp_field_get_type(field))!=IL2CPP_TYPE_I4)Fail("display registry version ABI");
        il2cpp_field_get_value(registry,field,&version);
        int count=Integer(Call(list,"get_Count",0,registry,nullptr));
        if(count<0||count>4096)Fail("display registry count");
        if(count){
            int first=0;void* args[]={&first};
            auto* fitter=Call(list,"get_Item",1,registry,args);
            auto* scaler=fitter?Read(fitter,Field(fitters,"scaler",0x20)):nullptr;
            if(scaler){
                auto value=VectorValue(Call(DiscoSceneResidency::Class("UnityEngine.UI.dll","UnityEngine.UI","CanvasScaler"),"get_referenceResolution",0,scaler,nullptr));
                matches=matches&&DiscoDisplay::MatchingReference(value.x,value.y,profile);
            }
        }
    }
    if(root){
        auto* rect=Read(root,Field(il2cpp_object_get_class(root),"rectTransform",0x18));
        if(rect){
            auto value=VectorValue(Call(DiscoSceneResidency::Class("UnityEngine.CoreModule.dll","UnityEngine","RectTransform"),"get_sizeDelta",0,rect,nullptr));
            matches=matches&&DiscoDisplay::MatchingReference(value.x,value.y,profile);
        }
    }
    return {uintptr_t(registry),uintptr_t(root),version};
}
#endif
static void Refresh() {
#ifdef __ANDROID__
    if (!DiscoAndroidUnityThread()) Fail("display refresh is not on Unity thread");
#else
    if (![[NSBundle.mainBundle objectForInfoDictionaryKey:@"DiscoFillViewport"] boolValue]) return;
    if (![NSThread isMainThread]) Fail("display refresh is not on Unity thread");
#endif
    Il2CppClass* screen = DiscoSceneResidency::Class("UnityEngine.CoreModule.dll", "UnityEngine", "Screen");
    int width = Integer(Call(screen, "get_width", 0, nullptr, nullptr));
    int height = Integer(Call(screen, "get_height", 0, nullptr, nullptr));
    DiscoDisplay::Profile profile;
    if (!DiscoDisplay::TabletProfile(width, height, profile)) return; // Rotation still in progress.
    int aspectMode = 3;
#ifdef __ANDROID__
    aspectMode = DiscoDisplay::NativeAspectMode(profile);
#endif
    Il2CppClass* aspect = DiscoSceneResidency::Class("Assembly-CSharp.dll", "", "AspectUtility");
    il2cpp_runtime_class_init(aspect);
    FieldInfo* singletonField = Field(aspect, "singleton", 0x10);
    Il2CppObject* singleton = nullptr;
    il2cpp_field_static_get_value(singletonField, &singleton);
    if (!singleton) return; // Original UI/cameras have not initialized yet.
    FieldInfo* ratioField = Field(aspect, "currentRatio", 0);
    int current = -1; il2cpp_field_static_get_value(ratioField, &current);
    Il2CppClass* scenes = DiscoSceneResidency::Class("UnityEngine.CoreModule.dll", "UnityEngine.SceneManagement", "SceneManager");
    int count = Integer(Call(scenes, "get_sceneCount", 0, nullptr, nullptr));
    int active = Integer(Call(scenes, "GetActiveScene", 0, nullptr, nullptr));
    static int previousWidth = 0, previousHeight = 0, previousCount = -1, previousActive = 0;
    bool sameLayout=true;
#ifndef __ANDROID__
    auto* layoutFitters=DiscoSceneResidency::Class("Assembly-CSharp.dll","","AspectRatioFitterUtility");
    auto* layoutGlobal=DiscoSceneResidency::Class("Assembly-CSharp.dll","","GlobalUIFitter");
    il2cpp_runtime_class_init(layoutFitters);il2cpp_runtime_class_init(layoutGlobal);
    auto* layoutRootField=il2cpp_class_get_field_from_name(layoutGlobal,"Singleton");
    if(!layoutRootField||!(il2cpp_field_get_flags(layoutRootField)&0x10))Fail("global UI singleton ABI");
    Il2CppObject* layoutRoot=nullptr;il2cpp_field_static_get_value(layoutRootField,&layoutRoot);
    auto owners=LayoutOwners(layoutFitters,layoutRoot,sameLayout,profile);
    static DiscoDisplay::LayoutOwners previousOwners={};
    sameLayout=sameLayout&&DiscoDisplay::SameOwners(owners,previousOwners);
#endif
    if (sameLayout && current == aspectMode && width == previousWidth && height == previousHeight && count == previousCount && active == previousActive) return;
    FieldInfo* wanted = Field(aspect, "wantedAspectRatio", 4);
    if (!(il2cpp_field_get_flags(wanted) & 0x10) || il2cpp_type_get_type(il2cpp_field_get_type(wanted)) != IL2CPP_TYPE_R4)
        Fail("display ratio field ABI");
    // The original camera helper handles modes 0..2 explicitly. Its 4:3 path
    // retains wantedAspectRatio, so set the validated ratio before invoking it.
    il2cpp_field_static_set_value(wanted, &profile.aspect);
    int horizontalBars = 0;
    void* args[] = { &aspectMode, &horizontalBars };
    Call(Method(aspect, "UpdateAspectRatio", 2, 0x71ac78), nullptr, args);
#ifdef __ANDROID__
    if (aspectMode != 3) {
        auto* global = DiscoSceneResidency::Class("Assembly-CSharp.dll", "", "GlobalUIFitter");
        void* globalArgs[] = { &aspectMode };
        Call(Method(global, "RefreshAspect", 1, 0x21f8028), nullptr, globalArgs);
        previousWidth=width; previousHeight=height; previousCount=count; previousActive=active;
        Log("NATIVE DISPLAY: original layout mode=%d viewport=%dx%d scene=%d\n", aspectMode,width,height,active);
        return;
    }
#endif
    Il2CppClass* fitters = DiscoSceneResidency::Class("Assembly-CSharp.dll", "", "AspectRatioFitterUtility");
    // The game's preset installs a fixed 4:3 fitter. Override it for the
    // actual tablet aspect without changing the existing reference height.
    void* fitterArgs[] = { &profile.aspect, &horizontalBars };
    Call(Method(fitters, "SetFitter", 2, 0xe0c268), nullptr, fitterArgs);
    // Normalize the source's 2372x2048 reference to the actual tablet display.
    // Keep a stable reference height; artwork and glyphs retain their aspect.
    struct Vector { float x, y; } reference = {profile.referenceWidth, profile.referenceHeight};
    static_assert(sizeof(reference) == 8, "Pinned Vector2 layout");
    float matchWidth = 0;
    void* scalerArgs[] = { &reference, &matchWidth };
    Call(Method(fitters, "SetScaler", 2, 0xe0c468), nullptr, scalerArgs);
    Il2CppClass* global = DiscoSceneResidency::Class("Assembly-CSharp.dll", "", "GlobalUIFitter");
    il2cpp_runtime_class_init(global);
    FieldInfo* globalField = il2cpp_class_get_field_from_name(global, "Singleton");
    if (!globalField || !(il2cpp_field_get_flags(globalField) & 0x10)) Fail("global UI singleton ABI");
    Il2CppObject* owner = nullptr;
    il2cpp_field_static_get_value(globalField, &owner);
    if (owner) {
        Il2CppObject* rect = Read(owner, Field(global, "rectTransform", 0x18));
        if (rect) {
            void* rectArgs[] = { &reference };
            Call(DiscoSceneResidency::Class("UnityEngine.CoreModule.dll", "UnityEngine", "RectTransform"), "set_sizeDelta", 1, rect, rectArgs);
        }
    }
    previousWidth=width; previousHeight=height; previousCount=count; previousActive=active;
#ifndef __ANDROID__
    previousOwners=owners;
#endif
    Log("NATIVE DISPLAY: game tablet profile=%dx%d reference=%.1fx%.1f scene=%d\n", width,height,reference.x,reference.y,active);
}
}
