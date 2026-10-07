// Original adapter around the supplied runtime's scene coroutines. No recovered
// method bodies are embedded here. Enabled explicitly for device experiments.
#pragma once
#include "il2cpp-class-internals.h"
#include "il2cpp-object-internals.h"
#include <string>
#include <vector>
#include "SceneLoadPolicy.h"

namespace DiscoSceneResidency {
static_assert(offsetof(Il2CppClass, vtable) == 0x138, "Pinned IL2CPP class layout changed");
static_assert(offsetof(MethodInfo, methodPointer) == 0, "Pinned method layout changed");
static_assert(offsetof(Il2CppArraySize, vector) == 0x20, "Pinned array layout changed");
using MoveNext = bool (*)(Il2CppObject*, const MethodInfo*);
static MoveNext preloadOriginal, transitionOriginal;
static Il2CppClass *fastClass, *sceneClass, *managerClass;
static FieldInfo *fastInstance, *skipField, *cacheField, *preloadOwner,
    *transitionState, *transitionName, *transitionCurrent;
static const MethodInfo *loadAsync, *preloadMethod, *transitionMethod;
static uint32_t preloadSkipHandle, pendingCoroutine, pendingOperation;

[[noreturn]] static void Fail(const char* message) {
    printf("NATIVE RESIDENCY: unsupported integration: %s\n", message);
    fflush(stdout); abort();
}
static Il2CppClass* Class(const char* assemblyName, const char* space, const char* name) {
    const Il2CppAssembly* assembly = il2cpp_domain_assembly_open(il2cpp_domain_get(), assemblyName);
    Il2CppClass* klass = assembly ? il2cpp_class_from_name(il2cpp_assembly_get_image(assembly), space, name) : nullptr;
    if (!klass) Fail(name);
    return klass;
}
static FieldInfo* Field(Il2CppClass* klass, const char* name, size_t offset) {
    FieldInfo* field = il2cpp_class_get_field_from_name(klass, name);
    if (!field || il2cpp_field_get_offset(field) != offset) Fail(name);
    return field;
}
static Il2CppObject* Read(Il2CppObject* owner, FieldInfo* field) {
    Il2CppObject* value = nullptr;
    if (!owner) Fail("missing field owner");
    il2cpp_field_get_value(owner, field, &value);
    return value;
}
static Il2CppObject* Fast() {
    Il2CppObject* instance = nullptr;
    il2cpp_field_static_get_value(fastInstance, &instance);
    if (!instance) Fail("FastLoadManager singleton absent");
    return instance;
}
static std::string Text(Il2CppString* string) {
    if (!string || il2cpp_string_length(string) < 0 || il2cpp_string_length(string) > 4096)
        Fail("invalid scene string");
    NSString* text = [NSString stringWithCharacters:(const unichar*)il2cpp_string_chars(string)
        length:il2cpp_string_length(string)];
    if (!text || !text.UTF8String) Fail("scene name encoding");
    return text.UTF8String;
}
static Il2CppObject* Call(const MethodInfo* method, void* owner, void** args) {
    if (!method) Fail("missing managed method");
    Il2CppException* exception = nullptr;
    Il2CppObject* result = il2cpp_runtime_invoke(method, owner, args, &exception);
    if (exception) {
        char detail[2048] = {};
        il2cpp_format_exception(exception, detail, sizeof(detail));
        printf("NATIVE RESIDENCY: method=%s exception=%s\n", il2cpp_method_get_name(method), detail);
        Fail("managed call failed");
    }
    return result;
}
static Il2CppObject* Call(Il2CppClass* klass, const char* name, int count, void* owner, void** args) {
    return Call(il2cpp_class_get_method_from_name(klass, name, count), owner, args);
}
static bool Boolean(Il2CppObject* value) {
    uint32_t alignment = 0;
    if (!value || il2cpp_class_value_size(il2cpp_object_get_class(value), &alignment) != 1)
        Fail("expected boxed Boolean");
    return *(bool*)il2cpp_object_unbox(value);
}
static int Integer(Il2CppObject* value) {
    uint32_t alignment = 0;
    if (!value || il2cpp_class_value_size(il2cpp_object_get_class(value), &alignment) != 4)
        Fail("expected boxed Int32/Scene");
    return *(int*)il2cpp_object_unbox(value);
}
static Il2CppArraySize* SkipArray(Il2CppObject* owner) {
    Il2CppObject* value = Read(owner, skipField);
    if (!value || il2cpp_class_get_rank(il2cpp_object_get_class(value)) != 1 ||
        il2cpp_array_length((Il2CppArray*)value) > 256) Fail("scene skip array layout");
    return (Il2CppArraySize*)value;
}
static bool Skipped(Il2CppArraySize* array, const std::string& target) {
    for (uint32_t i = 0; i < il2cpp_array_length(array); ++i)
        if (array->vector[i] && Text((Il2CppString*)array->vector[i]) == target) return true;
    return false;
}
static void PreparePreloadSkip(Il2CppObject* owner) {
    Il2CppArraySize* original = SkipArray(owner);
    Il2CppClass* utility = Class("UnityEngine.CoreModule.dll", "UnityEngine.SceneManagement", "SceneUtility");
    int count = Integer(Call(managerClass, "get_sceneCountInBuildSettings", 0, nullptr, nullptr));
    if (count <= 0 || count > 256) Fail("build scene count");
    std::vector<std::string> originalNames, paths;
    for (uint32_t i = 0; i < il2cpp_array_length(original); ++i) {
        if (!original->vector[i]) Fail("null original skip name");
        originalNames.push_back(Text((Il2CppString*)original->vector[i]));
    }
    for (int index = 0; index < count; ++index) {
        void* args[] = { &index };
        paths.push_back(Text((Il2CppString*)Call(utility, "GetScenePathByBuildIndex", 1, nullptr, args)));
    }
    DiscoScenePolicy::PreloadPlan plan;
    std::string error;
    if (!DiscoScenePolicy::Plan(paths, originalNames, plan, error)) Fail(error.c_str());
    // Keep the original first Single-mode load to clear startup scenes while
    // preserving the game's DontDestroyOnLoad bootstrap objects.
    printf("NATIVE RESIDENCY: bootstrap scene=%s\n", plan.bootstrap.c_str());
    const auto& skipped = plan.deferred;
    Il2CppClass* strings = Class("mscorlib.dll", "System", "String");
    Il2CppArraySize* array = (Il2CppArraySize*)il2cpp_array_new(strings, skipped.size());
    if (!array) Fail("skip array allocation");
    preloadSkipHandle = il2cpp_gchandle_new((Il2CppObject*)array, false);
    for (size_t i = 0; i < skipped.size(); ++i)
        il2cpp_gc_wbarrier_set_field((Il2CppObject*)array, &array->vector[i], il2cpp_string_new(skipped[i].c_str()));
    printf("NATIVE RESIDENCY: deferring %zu build scenes; original textures unchanged\n", skipped.size());
}
static bool Preload(Il2CppObject* coroutine, const MethodInfo* method) {
    if (![NSThread isMainThread]) Fail("preload is not on Unity thread");
    Il2CppObject* owner = Read(coroutine, preloadOwner);
    if (!preloadSkipHandle) PreparePreloadSkip(owner);
    Il2CppObject* saved = Read(owner, skipField);
    uint32_t savedHandle = il2cpp_gchandle_new(saved, false);
    il2cpp_field_set_value_object(owner, skipField, il2cpp_gchandle_get_target(preloadSkipHandle));
    bool running = preloadOriginal(coroutine, method);
    il2cpp_field_set_value_object(owner, skipField, il2cpp_gchandle_get_target(savedHandle));
    il2cpp_gchandle_free(savedHandle);
    if (!running) printf("NATIVE RESIDENCY: original bootstrap coroutine finished\n");
    return running;
}
static bool Transition(Il2CppObject* coroutine, const MethodInfo* method) {
    if (![NSThread isMainThread]) Fail("transition is not on Unity thread");
    int state = -1;
    il2cpp_field_get_value(coroutine, transitionState, &state);
    if (state != 0) return transitionOriginal(coroutine, method);
    Il2CppObject* owner = Fast();
    Il2CppString* name = (Il2CppString*)Read(coroutine, transitionName);
    std::string text = Text(name);
    if (Skipped(SkipArray(owner), text)) return transitionOriginal(coroutine, method);
    Il2CppObject* cache = Read(owner, cacheField);
    if (!cache) Fail("scene cache missing");
    void* nameArgs[] = { name };
    if (!pendingCoroutine && Boolean(Call(il2cpp_object_get_class(cache), "ContainsKey", 1, cache, nameArgs)))
        return transitionOriginal(coroutine, method);
    if (!pendingCoroutine) {
        int additive = 1;
        void* args[] = { name, &additive };
        Il2CppObject* operation = Call(loadAsync, nullptr, args);
        if (!operation) Fail("scene operation absent");
        pendingCoroutine = il2cpp_gchandle_new(coroutine, false);
        pendingOperation = il2cpp_gchandle_new(operation, false);
        printf("NATIVE RESIDENCY: demand load=%s\n", text.c_str());
    }
    if (il2cpp_gchandle_get_target(pendingCoroutine) != coroutine) Fail("overlapping scene transitions");
    Il2CppObject* operation = il2cpp_gchandle_get_target(pendingOperation);
    if (!operation) Fail("lost scene operation");
    if (!Boolean(Call(il2cpp_object_get_class(operation), "get_isDone", 0, operation, nullptr))) {
        // Keep original state zero. IEnumerator.Current yields the live operation
        // until loading is complete; the original transition then runs unchanged.
        il2cpp_field_set_value_object(coroutine, transitionCurrent, operation);
        return true;
    }
    size_t slash = text.find_last_of('/');
    Il2CppString* shortName = il2cpp_string_new(text.substr(slash == std::string::npos ? 0 : slash + 1).c_str());
    void* findArgs[] = { shortName };
    Il2CppObject* scene = Call(managerClass, "GetSceneByName", 1, nullptr, findArgs);
    int handle = Integer(scene);
    if (!handle || !Boolean(Call(sceneClass, "get_isLoaded", 0, il2cpp_object_unbox(scene), nullptr)))
        Fail("demand scene was not loaded");
    void* cacheArgs[] = { name, &handle };
    Call(il2cpp_object_get_class(cache), "set_Item", 2, cache, cacheArgs);
    void* processArgs[] = { &handle };
    Call(fastClass, "LoadProcessScene", 1, owner, processArgs);
    il2cpp_field_set_value_object(coroutine, transitionCurrent, nullptr);
    il2cpp_gchandle_free(pendingOperation); pendingOperation = 0;
    il2cpp_gchandle_free(pendingCoroutine); pendingCoroutine = 0;
    printf("NATIVE RESIDENCY: cached demand scene=%s handle=%d\n", text.c_str(), handle);
    return transitionOriginal(coroutine, method);
}
static Il2CppClass* Nested(Il2CppClass* parent, const char* name) {
    void* iterator = nullptr;
    while (Il2CppClass* klass = il2cpp_class_get_nested_types(parent, &iterator))
        if (!strcmp(il2cpp_class_get_name(klass), name)) return klass;
    Fail(name);
}
static const MethodInfo* ValidateHook(Il2CppClass* klass, uintptr_t offset) {
    il2cpp_runtime_class_init(klass);
    const MethodInfo* method = il2cpp_class_get_method_from_name(klass, "MoveNext", 0);
    Dl_info image = {};
    if (!method || !method->methodPointer || !dladdr((void*)method->methodPointer, &image) ||
        !image.dli_fname || !strstr(image.dli_fname, "/GameAssembly.framework/GameAssembly") ||
        (uintptr_t)method->methodPointer - (uintptr_t)image.dli_fbase != offset ||
        method->parameters_count != 0 || il2cpp_type_get_type(method->return_type) != IL2CPP_TYPE_BOOLEAN ||
        method->slot >= klass->vtable_count || klass->vtable_count > 64 ||
        klass->vtable[method->slot].methodPtr != method->methodPointer)
        Fail("coroutine method/vtable ABI differs from inspected reference");
    return method;
}
static void InstallHook(Il2CppClass* klass, const MethodInfo* method, MoveNext replacement, MoveNext* original) {
    *original = (MoveNext)method->methodPointer;
    // Only writable runtime metadata is changed. Signed executable pages and
    // the supplied reference binary remain immutable.
    for (unsigned slot = 0; slot < klass->vtable_count; ++slot)
        if (klass->vtable[slot].methodPtr == method->methodPointer)
            klass->vtable[slot].methodPtr = (Il2CppMethodPointer)replacement;
    const_cast<MethodInfo*>(method)->methodPointer = (Il2CppMethodPointer)replacement;
}
static void Install() {
    const char* enabled = getenv("DISCO_LAZY_SCENES");
    bool selected = enabled ? !strcmp(enabled, "1") : [[NSBundle.mainBundle objectForInfoDictionaryKey:@"DiscoLazyScenes"] boolValue];
    if (!selected) return;
    fastClass = Class("Assembly-CSharp.dll", "", "FastLoadManager");
    Il2CppClass* transitions = Class("Assembly-CSharp.dll", "FortressOccident", "SceneTransitionManager");
    sceneClass = Class("UnityEngine.CoreModule.dll", "UnityEngine.SceneManagement", "Scene");
    managerClass = Class("UnityEngine.CoreModule.dll", "UnityEngine.SceneManagement", "SceneManager");
    Il2CppClass* preload = Nested(fastClass, "<LoadAllScenes>d__8");
    Il2CppClass* transition = Nested(transitions, "<LoadSceneCoR>d__36");
    fastInstance = il2cpp_class_get_field_from_name(fastClass, "m_FastLoadManager");
    if (!fastInstance || !(il2cpp_field_get_flags(fastInstance) & 0x10)) Fail("singleton field is not static");
    skipField = Field(fastClass, "scenesToSkip", 0x30);
    cacheField = Field(fastClass, "allScenes", 0x28);
    preloadOwner = Field(preload, "<>4__this", 0x20);
    transitionState = Field(transition, "<>1__state", 0x10);
    transitionCurrent = Field(transition, "<>2__current", 0x18);
    transitionName = Field(transition, "sceneName", 0x20);
    void* iterator = nullptr;
    while (const MethodInfo* method = il2cpp_class_get_methods(managerClass, &iterator)) {
        if (strcmp(il2cpp_method_get_name(method), "LoadSceneAsync") || il2cpp_method_get_param_count(method) != 2 ||
            il2cpp_type_get_type(il2cpp_method_get_param(method, 0)) != IL2CPP_TYPE_STRING) continue;
        Il2CppClass* mode = il2cpp_class_from_type(il2cpp_method_get_param(method, 1));
        // Unity also exposes (string, LoadSceneParameters), a different value
        // type ABI. Select the enum overload explicitly before passing Int32.
        if (mode && !strcmp(il2cpp_class_get_namespace(mode), "UnityEngine.SceneManagement") &&
            !strcmp(il2cpp_class_get_name(mode), "LoadSceneMode")) {
            if (loadAsync) Fail("ambiguous scene load overload");
            loadAsync = method;
        }
    }
    if (!loadAsync) Fail("string/additive scene load overload absent");
    preloadMethod = ValidateHook(preload, 0x21cab90);
    transitionMethod = ValidateHook(transition, 0x2337a48);
    InstallHook(preload, preloadMethod, Preload, &preloadOriginal);
    InstallHook(transition, transitionMethod, Transition, &transitionOriginal);
    printf("NATIVE RESIDENCY: validated coroutine adapters installed; eviction is not enabled\n");
}
}
