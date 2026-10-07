// Original portable display policy. No supplied game code.
#pragma once
#include <cmath>
#include <cstdint>
namespace DiscoDisplay {
struct Profile { float aspect, referenceWidth, referenceHeight; };
inline bool TabletProfile(int32_t width, int32_t height, Profile& result) {
    result = {};
    if (width <= 0 || height <= 0 || width > 16384 || height > 16384 || width <= height) return false;
    float aspect = (float)width / (float)height;
    // Full-screen landscape iPads, including 11-inch and mini aspect ratios.
    // Reject portrait, external widescreen and transient invalid dimensions.
    if (aspect < 1.25f || aspect > 1.6f) return false;
    result = { aspect, 2048.0f * aspect, 2048.0f };
    return true;
}
}
