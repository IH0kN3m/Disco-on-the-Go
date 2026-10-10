#pragma once
namespace DiscoGraphicsFormat {
// Float32 represents every 16-bit UNorm level with greater precision than
// float16. Storage promotion still requires rendered-parity verification.
inline int Candidate(int format) {
    if(format==21)return 49; // R16_UNorm -> R32_SFloat
    if(format==22)return 50; // R16G16_UNorm -> R32G32_SFloat
    return format;
}
template<class Supported> int Compatible(int format,Supported supported) {
    int candidate=Candidate(format);
    return candidate!=format&&!supported(format,4)&&supported(candidate,4)?candidate:format;
}
}
