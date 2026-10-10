// Original iPad game host. The linked provider is derived locally from Disco.app.
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#import "UI/UnityAppController+ViewHandling.h"
#include "il2cpp-api.h"
#include <dlfcn.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <mach/mach.h>
#include <malloc/malloc.h>
#include <os/proc.h>
#include <cerrno>
#include "Unity/UnityInterface.h"
#include "DiscoSceneResidency.h"
#include "DiscoGameDisplay.h"
#include "DiscoDialogueText.h"
#include "DiscoTouchControls.h"

extern "C" bool Unity_il2cppNoExceptions() { return false; }
extern "C" void DiscoNativeEngineStage(const char* stage);

static void LogMemory(const char* event)
{
    task_vm_info_data_t info = {};
    mach_msg_type_number_t count = TASK_VM_INFO_COUNT;
    kern_return_t result = task_info(mach_task_self(), TASK_VM_INFO, (task_info_t)&info, &count);
    size_t available = 0;
    if (@available(iOS 13.0, *)) available = os_proc_available_memory();
    if (result == KERN_SUCCESS)
        printf("NATIVE MEMORY: %s footprint=%llu resident=%llu available=%llu\n", event,
               (unsigned long long)info.phys_footprint, (unsigned long long)info.resident_size, (unsigned long long)available);
    else printf("NATIVE MEMORY: task_info failed=%d\n", result);
}

extern "C" void DiscoNativeEngineMemoryWarning()
{
    LogMemory("warning");
    size_t released = malloc_zone_pressure_relief(nullptr, 0);
    printf("NATIVE MEMORY: allocator pressure relief released=%llu\n", (unsigned long long)released);
    LogMemory("after allocator pressure relief");
}

// A separate hardware check; this does not change Unity's format support table.
static void CheckMetalBC() {
    id<MTLDevice> device=MTLCreateSystemDefaultDevice();
    if (@available(iOS 16.4,*)) {
        if (!device || !device.supportsBCTextureCompression) {
            DiscoNativeEngineStage("unsupported GPU: native BC texture compression is required");
            abort();
        }
    } else { DiscoNativeEngineStage("unsupported OS for native BC textures"); abort(); }
#if !__has_feature(objc_arc)
    [device release];
#endif
}

extern "C" const char* DiscoNativeEngineDataRoot()
{
    static NSString* root;
    if (!root)
    {
        NSString* documents = NSSearchPathForDirectoriesInDomains(NSDocumentDirectory, NSUserDomainMask, YES).firstObject;
        root = [[documents stringByAppendingPathComponent:@"DiscoPortAssets"] copy];
        NSString* expected = [NSBundle.mainBundle objectForInfoDictionaryKey:@"DiscoAssetManifestSHA256"];
        NSString* ready = [NSString stringWithContentsOfFile:[root stringByAppendingPathComponent:@"ready.sha256"]
                                                   encoding:NSUTF8StringEncoding error:nil];
        NSString* settings = [root stringByAppendingPathComponent:@"Data/globalgamemanagers"];
        if (!expected || ![ready isEqualToString:expected] || ![NSFileManager.defaultManager fileExistsAtPath:settings])
        {
            DiscoNativeEngineStage("persistent assets absent or stale; deploy their checked manifest first");
            abort();
        }
        UnityUpdateNoBackupFlag(root.fileSystemRepresentation, 1);
        DiscoNativeEngineStage("using persistent asset directory");
    }
    return root.fileSystemRepresentation;
}

extern "C" void DiscoNativeEngineStage(const char* stage)
{
    printf("NATIVE ENGINE: %s\n", stage);
    LogMemory(stage);
    fflush(stdout);
}

extern "C" void DiscoNativeEngineBegin() {
    NSString* directory=NSSearchPathForDirectoriesInDomains(NSDocumentDirectory,NSUserDomainMask,YES).firstObject;
    NSString* path=[directory stringByAppendingPathComponent:@"native-engine.log"];
    freopen(path.fileSystemRepresentation,"w",stdout);
    dup2(fileno(stdout),fileno(stderr));setvbuf(stdout,nullptr,_IONBF,0);
    CheckMetalBC();
    DiscoNativeEngineStage("before UnityInitRuntime");
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

static NSString* SteamPluginPath;
static NSString* AmplifyPluginPath;
static const char* FindPlugin(const char* name)
{
    if (name && strcmp(name, "steam_api") == 0 && SteamPluginPath)
        return SteamPluginPath.fileSystemRepresentation;
    if (name && strcmp(name, "AmplifyTextureNative") == 0 && AmplifyPluginPath)
        return AmplifyPluginPath.fileSystemRepresentation;
    return name;
}

extern "C" void DiscoNativeEnginePlugins()
{
    il2cpp_set_find_plugin_callback(FindPlugin);
    const char* names[] = { "SteamAPI", "AmplifyTextureNative" };
    for (const char* name : names) {
        NSString* relative = [NSString stringWithFormat:@"Frameworks/%s.framework/%s", name, name];
        NSString* path = [NSBundle.mainBundle.bundlePath stringByAppendingPathComponent:relative];
        if (![NSFileManager.defaultManager fileExistsAtPath:path]) continue;
        void* library = dlopen(path.fileSystemRepresentation, RTLD_NOW | RTLD_GLOBAL);
        if (!library) { printf("NATIVE ENGINE: %s plugin load failed: %s\n", name, dlerror()); continue; }
        if (!strcmp(name, "SteamAPI")) SteamPluginPath = [path copy];
        else {
            const char* exports[] = { "CreatePageDecoder", "DestroyPageDecoder", "TranscodeCrunchToBC",
                "DecodePackedHeightRG", "CreatePrePassHistogram", "BuildPrePassHistogram" };
            for (const char* symbol : exports) if (!dlsym(library, symbol)) {
                printf("NATIVE AMPLIFY: expected CPU export absent=%s\n", symbol); fflush(stdout); abort();
            }
            AmplifyPluginPath = [path copy];
        }
        printf("NATIVE ENGINE: derived %s plugin loaded; device behavior under test\n", name);
    }
}

static void ConfigureLandscapeDisplay()
{
    if (![[NSBundle.mainBundle objectForInfoDictionaryKey:@"DiscoLandscapeDisplay"] boolValue]) return;
    // The supplied desktop metadata strips the mobile managed property
    // wrappers. Native bindings are registered by the complete iOS engine.
    // Exact prototypes are checked against the pinned CoreBindings LLVM IR;
    // EnabledOrientation flags are 1,2,4,8 (not ScreenOrientation values).
    using Enable = void (*)(int32_t, uint8_t);
    using Request = void (*)(int32_t);
    Enable enable = (Enable)il2cpp_resolve_icall("UnityEngine.Screen::SetOrientationEnabled");
    Request request = (Request)il2cpp_resolve_icall("UnityEngine.Screen::RequestOrientation");
    if (!enable || !request) { printf("NATIVE DISPLAY: pinned orientation bindings absent\n"); fflush(stdout); abort(); }
    enable(1, 0); enable(2, 0); enable(4, 1); enable(8, 1);
    request(3); // Pinned Unity LandscapeLeft; iOS LandscapeRight.
    printf("NATIVE DISPLAY: engine landscape requested; enabled=%d,%d,%d,%d requested=%d autorotate=%d\n",
        UnityIsOrientationEnabled(1), UnityIsOrientationEnabled(2), UnityIsOrientationEnabled(3),
        UnityIsOrientationEnabled(4), UnityRequestedScreenOrientation(), UnityShouldAutorotate());
    // Unity 2020's statusBarOrientation/attemptRotation calls predate the
    // window-scene geometry API. Commit its controller request, then request
    // the matching geometry from iPadOS after showGameUI finishes.
    dispatch_async(dispatch_get_main_queue(), ^{
        UnityAppController* controller = GetAppController();
        [controller checkOrientationRequest];
        UIWindowScene* scene = controller.window.windowScene;
        printf("NATIVE DISPLAY: requesting landscape scene; bounds=%.0fx%.0f orientation=%ld\n",
            controller.window.bounds.size.width, controller.window.bounds.size.height, (long)scene.interfaceOrientation);
        if (@available(iOS 16.0, *)) {
            [controller.rootViewController setNeedsUpdateOfSupportedInterfaceOrientations];
            UIWindowSceneGeometryPreferencesIOS* preferences = [[UIWindowSceneGeometryPreferencesIOS alloc]
                initWithInterfaceOrientations:UIInterfaceOrientationMaskLandscapeRight];
            [scene requestGeometryUpdateWithPreferences:preferences errorHandler:^(NSError* error) {
                printf("NATIVE DISPLAY: geometry request rejected=%s\n", error.description.UTF8String);
            }];
        }
    });
}

extern "C" void DiscoNativeEngineLoaded() {
    DiscoNativeEngineStage("UnityLoadApplication returned");
    DiscoSceneResidency::Install();
    DiscoDialogueText::Install();
    ConfigureLandscapeDisplay();
    dispatch_async(dispatch_get_main_queue(), ^{ DiscoTouchControls::Install(); });
    static dispatch_source_t displayTimer;
    displayTimer=dispatch_source_create(DISPATCH_SOURCE_TYPE_TIMER,0,0,dispatch_get_main_queue());
    dispatch_source_set_timer(displayTimer,dispatch_time(DISPATCH_TIME_NOW,NSEC_PER_SEC),NSEC_PER_SEC,NSEC_PER_SEC/10);
    dispatch_source_set_event_handler(displayTimer, ^{ DiscoGameDisplay::Refresh(); });
    dispatch_resume(displayTimer);
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW,2*NSEC_PER_SEC),dispatch_get_main_queue(), ^{
        auto* quality=DiscoSceneResidency::Class("UnityEngine.CoreModule.dll","UnityEngine","QualitySettings");
        int fullQuality=0;void* arguments[]={&fullQuality};
        DiscoSceneResidency::Call(quality,"set_masterTextureLimit",1,nullptr,arguments);
    });
}
