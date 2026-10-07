// Original display adapter using the supplied game's existing aspect helpers.
#pragma once
#include "DisplayProfile.h"
namespace DiscoGameDisplay {
using namespace DiscoSceneResidency;
static const MethodInfo* Method(Il2CppClass* klass, const char* name, int count, uintptr_t address, bool isStatic = true) {
    const MethodInfo* method = il2cpp_class_get_method_from_name(klass, name, count);
    Dl_info image = {};
    if (!method || bool(method->flags & 0x10) != isStatic || !dladdr((void*)method->methodPointer, &image) ||
        !image.dli_fname || !strstr(image.dli_fname, "/GameAssembly.framework/GameAssembly") ||
        (uintptr_t)method->methodPointer - (uintptr_t)image.dli_fbase != address)
        Fail("game display method differs from inspected reference");
    return method;
}
static void Refresh() {
    if (![[NSBundle.mainBundle objectForInfoDictionaryKey:@"DiscoFillViewport"] boolValue]) return;
    if (![NSThread isMainThread]) Fail("display refresh is not on Unity thread");
    Il2CppClass* screen = DiscoSceneResidency::Class("UnityEngine.CoreModule.dll", "UnityEngine", "Screen");
    int width = Integer(Call(screen, "get_width", 0, nullptr, nullptr));
    int height = Integer(Call(screen, "get_height", 0, nullptr, nullptr));
    DiscoDisplay::Profile profile;
    if (!DiscoDisplay::TabletProfile(width, height, profile)) return; // Rotation still in progress.
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
    if (current == 3 && width == previousWidth && height == previousHeight && count == previousCount && active == previousActive) return;
    FieldInfo* wanted = Field(aspect, "wantedAspectRatio", 4);
    if (!(il2cpp_field_get_flags(wanted) & 0x10) || il2cpp_type_get_type(il2cpp_field_get_type(wanted)) != IL2CPP_TYPE_R4)
        Fail("display ratio field ABI");
    // The original camera helper handles modes 0..2 explicitly. Its 4:3 path
    // retains wantedAspectRatio, so set the validated ratio before invoking it.
    il2cpp_field_static_set_value(wanted, &profile.aspect);
    int fourByThree = 3, horizontalBars = 0;
    void* args[] = { &fourByThree, &horizontalBars };
    Call(Method(aspect, "UpdateAspectRatio", 2, 0x71ac78), nullptr, args);
    Il2CppClass* fitters = DiscoSceneResidency::Class("Assembly-CSharp.dll", "", "AspectRatioFitterUtility");
    // Normalize the source's 2372x2048 reference to the actual 4:3 display.
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
    printf("NATIVE DISPLAY: game 4:3 profile=%dx%d reference=%.1fx%.1f scene=%d\n", width,height,reference.x,reference.y,active);
}
}
