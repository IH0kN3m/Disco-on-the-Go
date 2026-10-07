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
    // Only the selected 13-inch M4 landscape viewport. Do not silently apply
    // this game profile to an unrelated external display or portrait frame.
    if (std::fabs(aspect - 4.0f / 3.0f) > 0.005f) return false;
    result = { aspect, 2048.0f * aspect, 2048.0f };
    return true;
}
}
