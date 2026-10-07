// Original compatibility experiment for the pinned Unity 2020 Metal format ABI.
#import <Metal/Metal.h>
#include <cstdint>
#include <cstdio>

extern id<MTLDevice> DiscoEngineMetalDevice __asm("__ZN5metal8g_DeviceE");
static bool Supported() {
    if (@available(iOS 16.4, *)) return DiscoEngineMetalDevice && DiscoEngineMetalDevice.supportsBCTextureCompression;
    return false;
}

// Unity GraphicsFormat 96..109, in the pinned plugin API's declared order.
static const uint64_t formats[] = { 131,130,133,132,135,134,140,141,142,143,151,150,153,152 };
static int Index(uint64_t format) {
    for (int i = 0; i < 14; ++i) if (formats[i] == format) return i;
    return -1;
}

extern "C" uint64_t DiscoOriginalMetalPixelFormat(int, int*);
extern "C" int DiscoOriginalMetalUnityGraphicsFormat(uint64_t);
extern "C" int DiscoOriginalMetalPixelFormatElementSize(uint64_t);
extern "C" int DiscoOriginalMetalTextureFormatBlockSize(uint64_t);
extern "C" bool DiscoOriginalMetalIsCompressedPixelFormat(uint64_t);
extern "C" bool DiscoOriginalMetalIsFilterCompatible(uint64_t);
extern "C" bool DiscoOriginalMetalIsColorRenderable(uint64_t);
extern "C" bool DiscoOriginalMetalSupportsBlending(uint64_t);
extern "C" bool DiscoOriginalMetalIsTextureViewCompatible(uint64_t, uint64_t);
extern "C" void DiscoOriginalMetalInitFormatUsageFlags(void*);

uint64_t BCPixelFormat(int, int*) __asm("__ZN5metal11PixelFormatE14GraphicsFormatPS0_");
uint64_t BCPixelFormat(int format, int* actual) {
    if (Supported() && format >= 96 && format <= 109) { *actual = format; return formats[format - 96]; }
    return DiscoOriginalMetalPixelFormat(format, actual);
}
int BCUnityGraphicsFormat(uint64_t) __asm("__ZN5metal19UnityGraphicsFormatE14MTLPixelFormat");
int BCUnityGraphicsFormat(uint64_t format) {
    int index = Index(format);
    return Supported() && index >= 0 ? 96 + index : DiscoOriginalMetalUnityGraphicsFormat(format);
}
int BCElementSize(uint64_t) __asm("__ZN5metal22PixelFormatElementSizeE14MTLPixelFormat");
int BCElementSize(uint64_t format) {
    int index = Index(format);
    if (Supported() && index >= 0) return index < 2 || index == 6 || index == 7 ? 8 : 16;
    return DiscoOriginalMetalPixelFormatElementSize(format);
}
int BCBlockSize(uint64_t) __asm("__ZN5metal22TextureFormatBlockSizeE14MTLPixelFormat");
int BCBlockSize(uint64_t format) { return Supported() && Index(format) >= 0 ? 4 : DiscoOriginalMetalTextureFormatBlockSize(format); }
bool BCCompressed(uint64_t) __asm("__ZN5metal23IsCompressedPixelFormatE14MTLPixelFormat");
bool BCCompressed(uint64_t format) { return Supported() && Index(format) >= 0 ? true : DiscoOriginalMetalIsCompressedPixelFormat(format); }
bool BCFilter(uint64_t) __asm("__ZN5metal18IsFilterCompatibleE14MTLPixelFormat");
bool BCFilter(uint64_t format) { return Supported() && Index(format) >= 0 ? true : DiscoOriginalMetalIsFilterCompatible(format); }
bool BCRender(uint64_t) __asm("__ZN5metal17IsColorRenderableE14MTLPixelFormat");
bool BCRender(uint64_t format) { return Supported() && Index(format) >= 0 ? false : DiscoOriginalMetalIsColorRenderable(format); }
bool BCBlend(uint64_t) __asm("__ZN5metal16SupportsBlendingE14MTLPixelFormat");
bool BCBlend(uint64_t format) { return Supported() && Index(format) >= 0 ? false : DiscoOriginalMetalSupportsBlending(format); }
bool BCView(uint64_t, uint64_t) __asm("__ZN5metal23IsTextureViewCompatibleE14MTLPixelFormatS0_");
bool BCView(uint64_t left, uint64_t right) {
    int a = Index(left), b = Index(right);
    if (Supported() && (a >= 0 || b >= 0)) {
        if (a < 0 || b < 0) return false;
        // sRGB/linear views share a BC1/2/3/7 block layout. Signed formats do not.
        return a == b || (a / 2 == b / 2 && (a < 6 || a >= 12));
    }
    return DiscoOriginalMetalIsTextureViewCompatible(left, right);
}
void BCUsage(void*) __asm("__ZN5metal20InitFormatUsageFlagsEP12GraphicsCaps");
void BCUsage(void* caps) {
    DiscoOriginalMetalInitFormatUsageFlags(caps);
    if (!Supported()) return;
    // Offset is validated against the exact object hash and its LLVM structure.
    uint32_t* usage = reinterpret_cast<uint32_t*>(static_cast<char*>(caps) + 0x16c);
    for (int i = 96; i <= 109; ++i) usage[i] = 3; // Sample + Linear; no render-target claim.
    printf("NATIVE METAL: pinned engine BC sample/filter bridge enabled\n");
}
