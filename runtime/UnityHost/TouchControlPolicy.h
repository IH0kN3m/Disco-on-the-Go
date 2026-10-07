// Original portable gesture/key ownership policy.
#pragma once
#include <cmath>
#include <cstdint>

namespace DiscoTouch {
inline bool Stick(float dx, float dy, float radius, float& x, float& y) {
    x = y = 0;
    if (!std::isfinite(dx) || !std::isfinite(dy) || !std::isfinite(radius) || radius <= 0) return false;
    double length = std::hypot((double)dx, (double)dy);
    if (length <= radius * 0.08) return true;
    double divisor = length > radius ? length : radius;
    x = (float)(dx / divisor); y = (float)(dy / divisor); return true;
}
class Pinch {
    uintptr_t owner = 0;
    double previousScale = 1;
    static bool Valid(double scale) { return std::isfinite(scale) && scale >= 0.0001 && scale <= 10000; }
public:
    void Cancel() { owner = 0; previousScale = 1; }
    bool Begin(uintptr_t camera, bool eligible, double scale) {
        Cancel();
        if (!camera || !eligible || !Valid(scale)) return false;
        owner = camera; previousScale = scale; return true;
    }
    bool Change(uintptr_t camera, bool eligible, double scale, float& delta) {
        delta = 0;
        if (!owner || owner != camera || !eligible || !Valid(scale)) { Cancel(); return false; }
        // Increasing the original zoom factor moves out. Spread fingers to move in.
        delta = -0.25f * (float)std::log2(scale / previousScale);
        previousScale = scale; return true;
    }
};
class Keys {
    uint32_t held = 0;
public:
    bool Set(unsigned key, bool down) {
        if (key >= 32) return false;
        uint32_t bit = uint32_t(1) << key;
        bool changed = bool(held & bit) != down;
        if (down) held |= bit; else held &= ~bit;
        return changed;
    }
    uint32_t Cancel() { uint32_t result = held; held = 0; return result; }
};
}
