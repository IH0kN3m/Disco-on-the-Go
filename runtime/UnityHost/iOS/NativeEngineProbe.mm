// Original diagnostic host. The linked provider is the derived game module.
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

static bool DiagnosticsEnabled()
{
    static bool enabled = [[NSBundle.mainBundle objectForInfoDictionaryKey:@"DiscoDiagnostics"] boolValue];
    return enabled;
}

// Region residency is diagnostic accounting, not an additive footprint estimate:
// shared mappings may be counted more than once. No Unity calls on this thread.
static void LogMemoryRegions()
{
    // This inspection entry point is absent from the public iOS link stubs.
    // Resolve it only in the diagnostic host; absence must not block the game.
    typedef kern_return_t (*RegionQuery)(vm_map_t, vm_address_t*, vm_size_t*, natural_t*,
        vm_region_recurse_info_t, mach_msg_type_number_t*);
    static RegionQuery query = (RegionQuery)dlsym(RTLD_DEFAULT, "mach_vm_region_recurse");
    static bool reportedAbsent = false;
    if (!query) {
        if (!reportedAbsent) printf("NATIVE REGIONS: diagnostic query unavailable\n");
        reportedAbsent = true; return;
    }
    uint64_t resident[256] = {}, virtualBytes[256] = {};
    unsigned regions[256] = {}, scanned = 0;
    vm_address_t cursor = 0;
    natural_t depth = 0;
    vm_size_t pageSize = 0;
    mach_port_t host = mach_host_self();
    host_page_size(host, &pageSize);
    mach_port_deallocate(mach_task_self(), host);
    if (!pageSize) return;
    while (scanned < 65536 && depth <= 16) {
        vm_address_t address = cursor;
        vm_size_t size = 0;
        vm_region_submap_info_data_64_t info = {};
        mach_msg_type_number_t count = VM_REGION_SUBMAP_INFO_COUNT_64;
        kern_return_t status = query(mach_task_self(), &address, &size, &depth,
            (vm_region_recurse_info_t)&info, &count);
        if (status == KERN_INVALID_ADDRESS) break;
        if (status != KERN_SUCCESS || count != VM_REGION_SUBMAP_INFO_COUNT_64 || !size || address < cursor || size > UINT64_MAX - address) {
            printf("NATIVE REGIONS: scan failed status=%d\n", status); return;
        }
        if (info.is_submap) { cursor = address; ++depth; continue; }
        unsigned tag = info.user_tag < 255 ? info.user_tag : 255;
        resident[tag] += uint64_t(info.pages_resident) * pageSize;
        virtualBytes[tag] += size;
        ++regions[tag]; ++scanned;
        cursor = address + size;
    }
    printf("NATIVE REGIONS: mappings=%u page_size=%lu bounded=%d\n", scanned,
        (unsigned long)pageSize, scanned == 65536 || depth > 16);
    // Only the ten largest resident categories; addresses remain out of public docs.
    for (unsigned rank = 0; rank < 10; ++rank) {
        unsigned best = 0;
        for (unsigned tag = 1; tag < 256; ++tag) if (resident[tag] > resident[best]) best = tag;
        if (!resident[best]) break;
        printf("NATIVE REGIONS: tag=%u resident=%llu virtual=%llu mappings=%u\n", best,
            (unsigned long long)resident[best], (unsigned long long)virtualBytes[best], regions[best]);
        resident[best] = 0;
    }
}

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

static void LogGrantedMemoryPolicy(bool entitlements)
{
    // Read-only, diagnostic SPI from Apple's published XNU ABI. Never set a
    // process limit. Missing symbols or denied queries must not block the app.
    struct Limits { int32_t active; uint32_t activeFlags; int32_t inactive; uint32_t inactiveFlags; };
    static_assert(sizeof(Limits) == 16, "Unexpected diagnostic memory-policy ABI");
    using Query = int (*)(uint32_t, int32_t, uint32_t, void*, size_t);
    static Query query = (Query)dlsym(RTLD_DEFAULT, "memorystatus_control");
    static int previousActive = INT32_MIN, previousInactive = INT32_MIN;
    static bool warned = false;
    if (query) {
        Limits limits = {};
        if (query(8, getpid(), 0, &limits, sizeof(limits)) == 0) {
            if (limits.active != previousActive || limits.inactive != previousInactive) {
                printf("NATIVE POLICY: kernel active_limit_mib=%d inactive_limit_mib=%d fatal_active=%u fatal_inactive=%u\n",
                    limits.active, limits.inactive, limits.activeFlags & 1, limits.inactiveFlags & 1);
                previousActive = limits.active; previousInactive = limits.inactive;
            }
        } else if (!warned) { printf("NATIVE POLICY: kernel limit query denied errno=%d\n", errno); warned = true; }
    } else if (!warned) { printf("NATIVE POLICY: kernel limit query unavailable\n"); warned = true; }
    if (!entitlements) return;
    using CreateTask = CFTypeRef (*)(CFAllocatorRef);
    using CopyValue = CFTypeRef (*)(CFTypeRef, CFStringRef, CFErrorRef*);
    CreateTask create = (CreateTask)dlsym(RTLD_DEFAULT, "SecTaskCreateFromSelf");
    CopyValue copy = (CopyValue)dlsym(RTLD_DEFAULT, "SecTaskCopyValueForEntitlement");
    if (!create || !copy) { printf("NATIVE POLICY: live entitlement inspection unavailable\n"); return; }
    CFTypeRef task = create(kCFAllocatorDefault);
    if (!task) return;
    const char* keys[] = { "com.apple.developer.kernel.increased-memory-limit",
        "com.apple.developer.kernel.increased-debugging-memory-limit",
        "com.apple.developer.kernel.extended-virtual-addressing", "get-task-allow" };
    for (const char* key : keys) {
        CFStringRef name = CFStringCreateWithCString(kCFAllocatorDefault, key, kCFStringEncodingUTF8);
        CFErrorRef error = nullptr;
        CFTypeRef value = copy(task, name, &error);
        int granted = value && CFGetTypeID(value) == CFBooleanGetTypeID() ? CFBooleanGetValue((CFBooleanRef)value) : -1;
        printf("NATIVE POLICY: live %s=%d error=%ld\n", key, granted, error ? (long)CFErrorGetCode(error) : 0);
        if (value) CFRelease(value);
        if (error) CFRelease(error);
        CFRelease(name);
    }
    CFRelease(task);
}

static void LogTextureMemory(bool resolve)
{
    typedef unsigned long long (*Getter)();
    static Getter getters[4] = {};
    static bool checked = false;
    const char* names[] = { "UnityEngine.Texture::get_currentTextureMemory", "UnityEngine.Texture::get_totalTextureMemory",
        "UnityEngine.Texture::get_desiredTextureMemory", "UnityEngine.Texture::get_nonStreamingTextureMemory" };
    if (resolve && !checked) {
        checked = true;
        for (unsigned i = 0; i < 4; ++i) {
            // UInt64, no arguments in the pinned Unity 2020 native binding ABI.
            // These engine bindings exist even when their managed methods were stripped.
            getters[i] = (Getter)il2cpp_resolve_icall(names[i]);
            if (!getters[i]) printf("NATIVE TEXTURES: binding absent=%s\n", names[i]);
        }
    }
    for (unsigned i = 0; i < 4; ++i)
        if (getters[i]) printf("NATIVE TEXTURES: %s=%llu\n", names[i], getters[i]());
}

static void LogAllocations(bool resolve)
{
    typedef long long (*Getter)();
    static Getter getters[4] = {};
    static bool checked = false;
    const char* names[] = { "UnityEngine.Profiling.Profiler::GetTotalAllocatedMemoryLong",
        "UnityEngine.Profiling.Profiler::GetTotalReservedMemoryLong",
        "UnityEngine.Profiling.Profiler::GetTotalUnusedReservedMemoryLong",
        "UnityEngine.Profiling.Profiler::GetAllocatedMemoryForGraphicsDriver" };
    if (resolve && !checked) {
        checked = true;
        for (unsigned i = 0; i < 4; ++i) {
            getters[i] = (Getter)il2cpp_resolve_icall(names[i]);
            if (!getters[i]) printf("NATIVE ALLOCATIONS: binding absent=%s\n", names[i]);
        }
    }
    if (!checked) return;
    for (unsigned i = 0; i < 4; ++i)
        if (getters[i]) printf("NATIVE ALLOCATIONS: %s=%lld\n", names[i], getters[i]());
    printf("NATIVE ALLOCATIONS: managed_used=%lld managed_heap=%lld\n",
        (long long)il2cpp_gc_get_used_size(), (long long)il2cpp_gc_get_heap_size());
}

extern "C" void DiscoNativeEngineMemoryWarning()
{
    LogMemory("warning"); LogTextureMemory(false); LogAllocations(false);
    size_t released = malloc_zone_pressure_relief(nullptr, 0);
    printf("NATIVE MEMORY: allocator pressure relief released=%llu\n", (unsigned long long)released);
    LogMemory("after allocator pressure relief");
}

// A separate hardware check; this does not change Unity's format support table.
static void CheckMetalBC()
{
    @autoreleasepool {
        id<MTLDevice> device = MTLCreateSystemDefaultDevice();
        if (!device) { DiscoNativeEngineStage("Metal capability probe has no device"); return; }
        if (@available(iOS 16.4, *)) {
            printf("NATIVE METAL: device=%s BC=%d\n", device.name.UTF8String, device.supportsBCTextureCompression);
            if (!device.supportsBCTextureCompression) {
                DiscoNativeEngineStage("unsupported GPU: this build requires native BC texture compression");
                abort(); // Stop before loading game textures into an unbounded RGBA fallback.
            }
            if (!DiagnosticsEnabled()) {
#if !__has_feature(objc_arc)
                [device release];
#endif
                return;
            }
            MTLPixelFormat formats[] = { MTLPixelFormatBC1_RGBA, MTLPixelFormatBC3_RGBA,
                MTLPixelFormatBC7_RGBAUnorm, MTLPixelFormatBC6H_RGBUfloat };
            for (MTLPixelFormat format : formats) {
                MTLTextureDescriptor* descriptor = [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:format width:4 height:4 mipmapped:NO];
                descriptor.storageMode = MTLStorageModeShared;
                descriptor.usage = MTLTextureUsageShaderRead;
                id<MTLTexture> texture = [device newTextureWithDescriptor:descriptor];
                printf("NATIVE METAL: BC format=%lu allocation=%d\n", (unsigned long)format, texture != nil);
#if !__has_feature(objc_arc)
                [texture release];
#endif
            }
            MTLTextureDescriptor* descriptor = [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatBC1_RGBA width:4 height:4 mipmapped:NO];
            descriptor.storageMode = MTLStorageModeShared;
            descriptor.usage = MTLTextureUsageShaderRead;
            id<MTLTexture> texture = [device newTextureWithDescriptor:descriptor];
            // One BC1 block: RGB565 red endpoint and sixteen endpoint-zero selectors.
            unsigned char block[8] = { 0x00, 0xf8, 0, 0, 0, 0, 0, 0 };
            if (!texture) return;
            [texture replaceRegion:MTLRegionMake2D(0, 0, 4, 4) mipmapLevel:0 withBytes:block bytesPerRow:8];
            NSError* error = nil;
            NSString* source = @"#include <metal_stdlib>\nusing namespace metal;\nkernel void readBC(texture2d<float, access::read> t [[texture(0)]], device float4* out [[buffer(0)]]) { out[0] = t.read(uint2(0,0)); }";
            id<MTLLibrary> library = [device newLibraryWithSource:source options:nil error:&error];
            id<MTLFunction> function = [library newFunctionWithName:@"readBC"];
            id<MTLComputePipelineState> pipeline = function ? [device newComputePipelineStateWithFunction:function error:&error] : nil;
            id<MTLCommandQueue> queue = [device newCommandQueue];
            id<MTLBuffer> output = [device newBufferWithLength:4 * sizeof(float) options:MTLResourceStorageModeShared];
            if (pipeline && queue && output) {
                memset(output.contents, 0, output.length);
                id<MTLCommandBuffer> command = [queue commandBuffer];
                id<MTLComputeCommandEncoder> encoder = [command computeCommandEncoder];
                [encoder setComputePipelineState:pipeline];
                [encoder setTexture:texture atIndex:0];
                [encoder setBuffer:output offset:0 atIndex:0];
                [encoder dispatchThreadgroups:MTLSizeMake(1,1,1) threadsPerThreadgroup:MTLSizeMake(1,1,1)];
                [encoder endEncoding];
                [command commit];
                [command waitUntilCompleted];
                float* pixel = (float*)output.contents;
                bool passed = command.status == MTLCommandBufferStatusCompleted && pixel[0] == 1 && pixel[1] == 0 && pixel[2] == 0 && pixel[3] == 1;
                printf("NATIVE METAL: BC1 GPU readback=%d rgba=%.3f,%.3f,%.3f,%.3f\n", passed, pixel[0], pixel[1], pixel[2], pixel[3]);
                if (command.error) printf("NATIVE METAL: command error=%s\n", command.error.localizedDescription.UTF8String);
            } else printf("NATIVE METAL: probe setup failed=%s\n", error.localizedDescription.UTF8String);
#if !__has_feature(objc_arc)
            [output release]; [queue release]; [pipeline release]; [function release]; [library release]; [texture release];
#endif
        }
#if !__has_feature(objc_arc)
        [device release];
#endif
    }
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
    LogGrantedMemoryPolicy(false);
    fflush(stdout);
}

extern "C" void DiscoNativeEngineBegin()
{
    NSString* directory = NSSearchPathForDirectoriesInDomains(NSDocumentDirectory, NSUserDomainMask, YES).firstObject;
    NSString* path = [directory stringByAppendingPathComponent:@"native-engine.log"];
    freopen(path.fileSystemRepresentation, "w", stdout);
    dup2(fileno(stdout), fileno(stderr));
    setvbuf(stdout, nullptr, _IONBF, 0);
    printf("NATIVE MEMORY: physical=%llu\n", (unsigned long long)NSProcessInfo.processInfo.physicalMemory);
    LogGrantedMemoryPolicy(true);
    CheckMetalBC();
    for (NSString* filename in @[@"native-engine-frame.png", @"native-engine-frame-30.png", @"native-engine-frame-60.png"])
        [NSFileManager.defaultManager removeItemAtPath:[directory stringByAppendingPathComponent:filename] error:nil];
    Dl_info provider = {};
    dladdr((void*)&il2cpp_init, &provider);
    printf("NATIVE ENGINE: provider=%s\n", provider.dli_fname ? provider.dli_fname : "unknown");
    DiscoNativeEngineStage("before UnityInitRuntime");
    static dispatch_source_t memoryTimer;
    memoryTimer = dispatch_source_create(DISPATCH_SOURCE_TYPE_TIMER, 0, 0, dispatch_get_global_queue(QOS_CLASS_UTILITY, 0));
    dispatch_source_set_timer(memoryTimer, dispatch_time(DISPATCH_TIME_NOW, NSEC_PER_SEC), (DiagnosticsEnabled() ? 2 : 30) * NSEC_PER_SEC, NSEC_PER_SEC / 10);
    dispatch_source_set_event_handler(memoryTimer, ^{
        static unsigned samples = 0;
        LogMemory("sample");
        ++samples;
        if (DiagnosticsEnabled() && samples % 5 == 0) LogMemoryRegions();
        if (DiagnosticsEnabled() && samples == 600) dispatch_source_cancel(memoryTimer);
    });
    dispatch_resume(memoryTimer);
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

static void LogSceneOwnership()
{
    const Il2CppAssembly* assembly = il2cpp_domain_assembly_open(il2cpp_domain_get(), "UnityEngine.CoreModule.dll");
    const Il2CppImage* image = assembly ? il2cpp_assembly_get_image(assembly) : nullptr;
    Il2CppClass* manager = image ? il2cpp_class_from_name(image, "UnityEngine.SceneManagement", "SceneManager") : nullptr;
    Il2CppClass* sceneClass = image ? il2cpp_class_from_name(image, "UnityEngine.SceneManagement", "Scene") : nullptr;
    if (!manager || !sceneClass || !il2cpp_class_is_valuetype(sceneClass)) return;
    Il2CppObject* countValue = Invoke(manager, "get_sceneCount", 0, nullptr, nullptr);
    if (!countValue) return;
    int count = *(int*)il2cpp_object_unbox(countValue);
    if (count < 0 || count > 256) { printf("NATIVE SCENES: unsupported count=%d\n", count); return; }
    Il2CppObject* active = Invoke(manager, "GetActiveScene", 0, nullptr, nullptr);
    int handle = active ? *(int*)il2cpp_object_unbox(active) : 0;
    static int previousCount = -1, previousActive = -1;
    if (count == previousCount && handle == previousActive) return;
    previousCount = count; previousActive = handle;
    printf("NATIVE SCENES: count=%d active_handle=%d\n", count, handle);
    for (int index = 0; index < count; ++index) {
        void* arguments[] = { &index };
        Il2CppObject* scene = Invoke(manager, "GetSceneAt", 1, nullptr, arguments);
        if (!scene) continue;
        void* value = il2cpp_object_unbox(scene);
        Il2CppString* name = (Il2CppString*)Invoke(sceneClass, "get_name", 0, value, nullptr);
        Il2CppObject* loaded = Invoke(sceneClass, "get_isLoaded", 0, value, nullptr);
        Il2CppObject* roots = Invoke(sceneClass, "get_rootCount", 0, value, nullptr);
        NSString* text = name ? [NSString stringWithCharacters:(const unichar*)il2cpp_string_chars(name)
            length:il2cpp_string_length(name)] : @"<unavailable>";
        printf("NATIVE SCENES: index=%d active=%d loaded=%d roots=%d name=%s\n", index,
            *(int*)value == handle, loaded ? *(bool*)il2cpp_object_unbox(loaded) : -1,
            roots ? *(int*)il2cpp_object_unbox(roots) : -1, text.UTF8String);
    }
}

static void CheckEngine()
{
    DiscoNativeEngineStage("checking live engine binding");
    static bool loggedPaths = false;
    if (!loggedPaths)
    {
        loggedPaths = true;
        const char* pathMethods[] = { "get_dataPath", "get_streamingAssetsPath" };
        for (const char* name : pathMethods)
        {
            Il2CppString* value = (Il2CppString*)Invoke(CoreClass("Application"), name, 0, nullptr, nullptr);
            if (value)
            {
                NSString* path = [NSString stringWithCharacters:(const unichar*)il2cpp_string_chars(value) length:il2cpp_string_length(value)];
                printf("NATIVE ENGINE: %s=%s\n", name, path.UTF8String);
            }
        }
    }
    const char* option = getenv("DISCO_TEXTURE_MIP_LIMIT");
    if (option && strlen(option) == 1 && option[0] >= '0' && option[0] <= '3')
    {
        int requested = option[0] - '0';
        Il2CppObject* current = Invoke(CoreClass("QualitySettings"), "get_masterTextureLimit", 0, nullptr, nullptr);
        static bool loggedLimit = false;
        if (current && *(int*)il2cpp_object_unbox(current) != requested)
        {
            void* arguments[] = { &requested };
            Invoke(CoreClass("QualitySettings"), "set_masterTextureLimit", 1, nullptr, arguments);
            Il2CppObject* actual = Invoke(CoreClass("QualitySettings"), "get_masterTextureLimit", 0, nullptr, nullptr);
            if (actual) { printf("NATIVE ENGINE: diagnostic texture mip limit=%d\n", *(int*)il2cpp_object_unbox(actual)); loggedLimit = true; }
        }
        else if (current && !loggedLimit) { printf("NATIVE ENGINE: diagnostic texture mip limit=%d\n", *(int*)il2cpp_object_unbox(current)); loggedLimit = true; }
    }
    Il2CppObject* frame = Invoke(CoreClass("Time"), "get_frameCount", 0, nullptr, nullptr);
    Il2CppObject* time = Invoke(CoreClass("Time"), "get_realtimeSinceStartup", 0, nullptr, nullptr);
    if (frame && time)
        printf("NATIVE ENGINE: original runtime engine call frame=%d time=%.3f\n",
               *(int*)il2cpp_object_unbox(frame), *(float*)il2cpp_object_unbox(time));
    const char* screenMethods[] = { "get_width", "get_height", "get_orientation" };
    for (const char* name : screenMethods) {
        Il2CppObject* value = Invoke(CoreClass("Screen"), name, 0, nullptr, nullptr);
        if (value) printf("NATIVE SCREEN: %s=%d\n", name, *(int*)il2cpp_object_unbox(value));
    }
    LogTextureMemory(true);
    LogAllocations(true);
    LogSceneOwnership();
    static bool checkedFormats = false;
    if (!checkedFormats) {
        checkedFormats = true;
        int formats[] = { 10, 12, 24, 25 }; // Unity 2020: DXT1, DXT5, BC6H, BC7.
        for (int format : formats) {
            void* arguments[] = { &format };
            Il2CppObject* supported = Invoke(CoreClass("SystemInfo"), "SupportsTextureFormat", 1, nullptr, arguments);
            if (supported) printf("NATIVE TEXTURES: Unity format=%d supported=%d\n", format, *(bool*)il2cpp_object_unbox(supported));
        }
    }
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

extern "C" void DiscoNativeEngineLoaded()
{
    DiscoNativeEngineStage("UnityLoadApplication returned");
    DiscoSceneResidency::Install();
    DiscoDialogueText::Install();
    ConfigureLandscapeDisplay();
    dispatch_async(dispatch_get_main_queue(), ^{ DiscoTouchControls::Install(); });
    static dispatch_source_t displayTimer;
    displayTimer = dispatch_source_create(DISPATCH_SOURCE_TYPE_TIMER, 0, 0, dispatch_get_main_queue());
    dispatch_source_set_timer(displayTimer, dispatch_time(DISPATCH_TIME_NOW, NSEC_PER_SEC), NSEC_PER_SEC, NSEC_PER_SEC / 10);
    dispatch_source_set_event_handler(displayTimer, ^{ DiscoGameDisplay::Refresh(); });
    dispatch_resume(displayTimer);
    // Normal play retains one startup check and lightweight memory-warning logs.
    // Allocator/scene walks and GPU screenshot readbacks are opt-in diagnostics.
    if (!DiagnosticsEnabled()) {
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 2 * NSEC_PER_SEC), dispatch_get_main_queue(), ^{ CheckEngine(); });
        return;
    }
    static dispatch_source_t allocationTimer;
    allocationTimer = dispatch_source_create(DISPATCH_SOURCE_TYPE_TIMER, 0, 0, dispatch_get_main_queue());
    dispatch_source_set_timer(allocationTimer, dispatch_time(DISPATCH_TIME_NOW, 5 * NSEC_PER_SEC),
        5 * NSEC_PER_SEC, NSEC_PER_SEC / 10);
    dispatch_source_set_event_handler(allocationTimer, ^{
        static unsigned samples = 0;
        LogTextureMemory(true);
        LogAllocations(true);
        LogGrantedMemoryPolicy(false);
        LogSceneOwnership();
        DiscoTouchControls::LogController();
        if (++samples == 240) dispatch_source_cancel(allocationTimer);
    });
    dispatch_resume(allocationTimer);
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
