// Original dialogue readability policy; supplied font values remain runtime data.
#pragma once
#include <cstddef>
#include <cstdint>
#include <cmath>
namespace DiscoDialogue {
inline bool LargerPresets(const int32_t* source, size_t count, int32_t* result) {
    if (!source || !result || count != 4) return false;
    int32_t enlarged[4];
    for (size_t i=0; i<count; ++i) {
        if (source[i]<8 || source[i]>128 || (i && source[i]<=source[i-1])) return false;
        enlarged[i]=int32_t(std::round(source[i]*1.125));
    }
    for (size_t i=0; i<count; ++i) result[i]=enlarged[i];
    return true;
}
}
