// Original portable display policy. No supplied game code.
#pragma once
#include <cmath>
#include <cstdint>
namespace DiscoDisplay {
struct Profile { float aspect, referenceWidth, referenceHeight; };
struct LayoutOwners {
    uintptr_t registry,root;
    int32_t registryVersion;
};
inline bool SameOwners(const LayoutOwners& a,const LayoutOwners& b) {
    return a.registry==b.registry&&a.root==b.root&&a.registryVersion==b.registryVersion;
}
inline bool MatchingReference(float x,float y,const Profile& profile) {
    return std::isfinite(x)&&std::isfinite(y)&&std::fabs(x-profile.referenceWidth)<0.5f&&
           std::fabs(y-profile.referenceHeight)<0.5f;
}
inline int NativeAspectMode(const Profile& profile) {
    // Accept small differences from rounded physical panel dimensions.
    if (std::fabs(profile.aspect-16.0f/10.0f)<0.01f) return 2;
    if (std::fabs(profile.aspect-16.0f/9.0f)<0.01f) return 0;
    return 3; // Existing custom tablet fitting path.
}
inline bool TabletProfile(int32_t width, int32_t height, Profile& result) {
    result = {};
    if (width <= 0 || height <= 0 || width > 16384 || height > 16384 || width <= height) return false;
    float aspect = (float)width / (float)height;
    // Landscape tablets, including rounded 16:10 and 16:9 Android displays.
    // Reject portrait, ultrawide and transient invalid dimensions.
    if (aspect < 1.25f || aspect > 1.8f) return false;
    result = { aspect, 2048.0f * aspect, 2048.0f };
    return true;
}
}
