// Original compatibility policy for the pinned Amplify OpenGL-only branches.
#pragma once
#include <cstdint>
namespace DiscoAmplifyCoordinates {
inline int DeviceType(int actual, uintptr_t caller) {
    // Both branches compare exclusively with OpenGLCore (17). GLES (11)
    // has the same framebuffer origin. Other game/backend decisions retain
    // the real device type; this is not a global platform override.
    if(actual==11&&(caller==0x1af6430||caller==0x156af68))return 17;
    return actual;
}
}
