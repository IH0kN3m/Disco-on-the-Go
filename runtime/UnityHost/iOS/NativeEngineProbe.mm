// Original diagnostic host. The linked provider is the derived game module.
#import <Foundation/Foundation.h>
#include "il2cpp-api.h"
#include <dlfcn.h>
#include <cstdio>
#include <cstring>
#include "Unity/UnityInterface.h"

extern "C" bool Unity_il2cppNoExceptions() { return false; }

extern "C" void DiscoNativeEngineStage(const char* stage)
{
    printf("NATIVE ENGINE: %s\n", stage);
    fflush(stdout);
}

extern "C" void DiscoNativeEngineBegin()
{
    NSString* directory = NSSearchPathForDirectoriesInDomains(NSDocumentDirectory, NSUserDomainMask, YES).firstObject;
    NSString* path = [directory stringByAppendingPathComponent:@"native-engine.log"];
    freopen(path.fileSystemRepresentation, "w", stdout);
    dup2(fileno(stdout), fileno(stderr));
    setvbuf(stdout, nullptr, _IONBF, 0);
    Dl_info provider = {};
    dladdr((void*)&il2cpp_init, &provider);
    printf("NATIVE ENGINE: provider=%s\n", provider.dli_fname ? provider.dli_fname : "unknown");
    DiscoNativeEngineStage("before UnityInitRuntime");
}

static Il2CppClass* CoreClass(const char* name)
{
    const Il2CppAssembly* assembly = il2cpp_domain_assembly_open(il2cpp_domain_get(), "UnityEngine.CoreModule.dll");
    return assembly ? il2cpp_class_from_name(il2cpp_assembly_get_image(assembly), "UnityEngine", name) : nullptr;
}

extern "C" void DiscoUpdateMuteState(int state)
{
    static bool checked = false, supported = false;
    if (!checked)
    {
        checked = true;
        const Il2CppAssembly* assembly = il2cpp_domain_assembly_open(il2cpp_domain_get(), "UnityEngine.AudioModule.dll");
        Il2CppClass* audio = assembly ? il2cpp_class_from_name(il2cpp_assembly_get_image(assembly), "UnityEngine", "AudioSettings") : nullptr;
        void* iterator = nullptr;
        while (audio)
        {
            Il2CppClass* nested = il2cpp_class_get_nested_types(audio, &iterator);
            if (!nested) break;
            if (strcmp(il2cpp_class_get_name(nested), "Mobile") == 0)
                supported = il2cpp_class_get_method_from_name(nested, "InvokeOnMuteStateChanged", 1) != nullptr;
        }
        if (!supported) DiscoNativeEngineStage("desktop metadata lacks mobile mute callback; host notification skipped");
    }
    if (supported) UnityUpdateMuteState(state);
}

static Il2CppObject* Invoke(Il2CppClass* klass, const char* name, int count, void* object, void** arguments)
{
    const MethodInfo* method = klass ? il2cpp_class_get_method_from_name(klass, name, count) : nullptr;
    if (!method) { printf("NATIVE ENGINE: missing method %s\n", name); return nullptr; }
    Il2CppException* exception = nullptr;
    Il2CppObject* result = il2cpp_runtime_invoke(method, object, arguments, &exception);
    if (exception)
    {
        char message[2048] = {};
        il2cpp_format_exception(exception, message, sizeof(message));
        printf("NATIVE ENGINE: exception %s: %s\n", name, message);
        return nullptr;
    }
    return result;
}

static void CheckEngine()
{
    DiscoNativeEngineStage("checking live engine binding");
    Il2CppObject* frame = Invoke(CoreClass("Time"), "get_frameCount", 0, nullptr, nullptr);
    Il2CppObject* time = Invoke(CoreClass("Time"), "get_realtimeSinceStartup", 0, nullptr, nullptr);
    if (frame && time)
        printf("NATIVE ENGINE: original runtime engine call frame=%d time=%.3f\n",
               *(int*)il2cpp_object_unbox(frame), *(float*)il2cpp_object_unbox(time));
}

static NSString* SteamPluginPath;
static const char* FindPlugin(const char* name)
{
    if (name && strcmp(name, "steam_api") == 0 && SteamPluginPath)
        return SteamPluginPath.fileSystemRepresentation;
    return name;
}

extern "C" void DiscoNativeEnginePlugins()
{
    NSString* path = [NSBundle.mainBundle.bundlePath stringByAppendingPathComponent:@"Frameworks/SteamAPI.framework/SteamAPI"];
    if (![NSFileManager.defaultManager fileExistsAtPath:path]) return;
    void* library = dlopen(path.fileSystemRepresentation, RTLD_NOW | RTLD_GLOBAL);
    if (!library) { printf("NATIVE ENGINE: Steam plugin load failed: %s\n", dlerror()); return; }
    SteamPluginPath = [path copy];
    il2cpp_set_find_plugin_callback(FindPlugin);
    DiscoNativeEngineStage("derived Steam plugin loaded; service compatibility untested");
}

static void CaptureEngine(const char* filename)
{
    const Il2CppAssembly* assembly = il2cpp_domain_assembly_open(il2cpp_domain_get(), "UnityEngine.ScreenCaptureModule.dll");
    Il2CppClass* klass = assembly ? il2cpp_class_from_name(il2cpp_assembly_get_image(assembly), "UnityEngine", "ScreenCapture") : nullptr;
    // The iOS screenshot backend prefixes the app's Documents directory.
    Il2CppString* path = il2cpp_string_new(filename);
    void* arguments[] = { path };
    Invoke(klass, "CaptureScreenshot", 1, nullptr, arguments);
    DiscoNativeEngineStage("screenshot requested through original runtime");
}

extern "C" void DiscoNativeEngineLoaded()
{
    DiscoNativeEngineStage("UnityLoadApplication returned");
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 2 * NSEC_PER_SEC), dispatch_get_main_queue(), ^{
        CheckEngine();
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 2 * NSEC_PER_SEC), dispatch_get_main_queue(), ^{ CheckEngine(); });
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 8 * NSEC_PER_SEC), dispatch_get_main_queue(), ^{ CaptureEngine("native-engine-frame.png"); });
    });
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 30 * NSEC_PER_SEC), dispatch_get_main_queue(), ^{
        CheckEngine();
        CaptureEngine("native-engine-frame-30.png");
    });
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 60 * NSEC_PER_SEC), dispatch_get_main_queue(), ^{
        CheckEngine();
        CaptureEngine("native-engine-frame-60.png");
    });
}
