// Original Android diagnostic. Optional source arithmetic is linked from local artifacts.
#include <jni.h>
#include <android/asset_manager_jni.h>
#include <vulkan/vulkan.h>
#include <unistd.h>
#include <sstream>
#include <string>
#include <vector>
#include <cmath>

std::string DiscoShaderReport(AAssetManager*);
std::string DiscoRuntimeReport(AAssetManager*);

struct Vector3 { float x, y, z; };
static_assert(sizeof(Vector3) == 12, "ARM64 homogeneous float aggregate");
#ifdef DISCO_ORIGINAL_KERNEL
extern "C" float DiscoOriginalDot(Vector3, Vector3, const void*);
#endif

static std::string Quote(const char* text) {
    std::string out = "\"";
    for (const unsigned char* p = reinterpret_cast<const unsigned char*>(text); *p; ++p) {
        if (*p == '\\' || *p == '"') { out += '\\'; out += char(*p); }
        else if (*p >= 32 && *p < 127) out += char(*p);
        else out += '?';
    }
    return out + '"';
}

extern "C" JNIEXPORT jstring JNICALL
Java_org_discoport_androidprobe_ProbeActivity_nativeReport(JNIEnv* env, jclass, jobject manager) {
    std::ostringstream out;
    out << "{\"page_size\":" << sysconf(_SC_PAGESIZE);
#ifdef DISCO_ORIGINAL_KERNEL
    const float a = DiscoOriginalDot({1,2,3}, {4,5,6}, nullptr);
    const float b = DiscoOriginalDot({-1,2,-3}, {4,-5,6}, nullptr);
    const float c = DiscoOriginalDot({0,0,0}, {4,5,6}, nullptr);
    out << ",\"original_arm64_leaf_present\":true,\"original_dot_result\":" << (std::isfinite(a) ? a : 0)
        << ",\"original_leaf_tests_passed\":" << (a == 32 && b == -32 && c == 0 ? "true" : "false");
#else
    out << ",\"original_arm64_leaf_present\":false";
#endif
    VkApplicationInfo application = {VK_STRUCTURE_TYPE_APPLICATION_INFO};
    application.pApplicationName = "Disco Android Probe";
    application.apiVersion = VK_API_VERSION_1_0;
    VkInstanceCreateInfo create = {VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};
    create.pApplicationInfo = &application;
    VkInstance instance = VK_NULL_HANDLE;
    VkResult result = vkCreateInstance(&create, nullptr, &instance);
    out << ",\"vulkan_instance_result\":" << int(result) << ",\"gpus\":[";
    if (result == VK_SUCCESS) {
        uint32_t count = 0;
        result = vkEnumeratePhysicalDevices(instance, &count, nullptr);
        if (result == VK_SUCCESS && count > 0 && count <= 16) {
            std::vector<VkPhysicalDevice> devices(count);
            result = vkEnumeratePhysicalDevices(instance, &count, devices.data());
            if (result == VK_SUCCESS) for (uint32_t i = 0; i < count; ++i) {
                VkPhysicalDeviceProperties properties;
                VkPhysicalDeviceFeatures features;
                vkGetPhysicalDeviceProperties(devices[i], &properties);
                vkGetPhysicalDeviceFeatures(devices[i], &features);
                if (i) out << ',';
                out << "{\"name\":" << Quote(properties.deviceName)
                    << ",\"api_version\":" << properties.apiVersion
                    << ",\"bc_feature\":" << (features.textureCompressionBC ? "true" : "false")
                    << ",\"astc_ldr_feature\":" << (features.textureCompressionASTC_LDR ? "true" : "false")
                    << ",\"etc2_feature\":" << (features.textureCompressionETC2 ? "true" : "false")
                    << ",\"formats\":[";
                const VkFormat formats[] = {VK_FORMAT_BC1_RGBA_UNORM_BLOCK, VK_FORMAT_BC3_UNORM_BLOCK,
                    VK_FORMAT_BC6H_UFLOAT_BLOCK, VK_FORMAT_BC7_UNORM_BLOCK, VK_FORMAT_ASTC_4x4_UNORM_BLOCK};
                const char* names[] = {"BC1", "BC3", "BC6H", "BC7", "ASTC4x4"};
                for (unsigned f = 0; f < 5; ++f) {
                    VkFormatProperties format;
                    vkGetPhysicalDeviceFormatProperties(devices[i], formats[f], &format);
                    if (f) out << ',';
                    out << "{\"name\":" << Quote(names[f]) << ",\"optimal_features\":" << format.optimalTilingFeatures
                        << ",\"sampled\":" << ((format.optimalTilingFeatures & VK_FORMAT_FEATURE_SAMPLED_IMAGE_BIT) ? "true" : "false")
                        << ",\"linear_filter\":" << ((format.optimalTilingFeatures & VK_FORMAT_FEATURE_SAMPLED_IMAGE_FILTER_LINEAR_BIT) ? "true" : "false") << '}';
                }
                out << "]}";
            }
        }
        vkDestroyInstance(instance, nullptr);
    }
    out << "],\"gles_shader_trial\":" << DiscoShaderReport(AAssetManager_fromJava(env,manager))
        << ",\"mapped_runtime_trial\":" << DiscoRuntimeReport(AAssetManager_fromJava(env,manager)) << "}";
    return env->NewStringUTF(out.str().c_str());
}
