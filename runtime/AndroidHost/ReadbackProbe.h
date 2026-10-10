#pragma once
#include "AmplifyReadback.h"
static std::string ReadbackProbe() {
    using namespace DiscoAmplifyReadback;
    const uint8_t expected[]={0,1,2,3,51,62,73,84,128,145,176,199,255,254,253,252};
    GLuint texture;glGenTextures(1,&texture);glBindTexture(GL_TEXTURE_2D,texture);
    glTexStorage2D(GL_TEXTURE_2D,1,GL_RGBA8,2,2);
    glTexSubImage2D(GL_TEXTURE_2D,0,0,0,2,2,GL_RGBA,GL_UNSIGNED_BYTE,expected);
    void* handle=Create(reinterpret_cast<void*>(uintptr_t(texture)),2,2);
    glPixelStorei(GL_PACK_ALIGNMENT,8);glPixelStorei(GL_PACK_ROW_LENGTH,9);
    glPixelStorei(GL_PACK_SKIP_ROWS,4);glPixelStorei(GL_PACK_SKIP_PIXELS,2);
    Issue(handle);Issue(handle);Render(0);
    uint8_t actual[24];std::memset(actual,0xab,sizeof(actual));Pixels(handle,actual+4);
    bool valid=std::memcmp(actual+4,expected,16)==0;
    for(int i=0;i<4;++i)valid=valid&&actual[i]==0xab&&actual[20+i]==0xab;
    GLint value;glGetIntegerv(GL_PACK_ALIGNMENT,&value);valid=valid&&value==8;
    glGetIntegerv(GL_PACK_ROW_LENGTH,&value);valid=valid&&value==9;
    glGetIntegerv(GL_PACK_SKIP_ROWS,&value);valid=valid&&value==4;
    glGetIntegerv(GL_PACK_SKIP_PIXELS,&value);valid=valid&&value==2;
    Issue(handle);Destroy(handle);glDeleteTextures(1,&texture);Render(0);
    valid=valid&&glGetError()==GL_NO_ERROR&&owned.empty()&&pending.empty();
    glPixelStorei(GL_PACK_ALIGNMENT,4);glPixelStorei(GL_PACK_ROW_LENGTH,0);glPixelStorei(GL_PACK_SKIP_ROWS,0);glPixelStorei(GL_PACK_SKIP_PIXELS,0);
    return std::string("{\"pixels_guards_state_and_retirement\":")+(valid?"true":"false")+"}";
}
