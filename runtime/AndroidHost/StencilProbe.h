// Original lossless stencil-copy experiment, run only in the offscreen probe.
#pragma once
#include <GLES3/gl3.h>
#include "StencilPrograms.h"
static std::string StencilProbe() {
    while(glGetError()!=GL_NO_ERROR){}
    GLuint fb[3]{},tex[3]{},depth=0,program=0,shaders[2]{};
    glGenFramebuffers(3,fb);glGenTextures(3,tex);glGenRenderbuffers(1,&depth);
    glBindFramebuffer(GL_FRAMEBUFFER,fb[0]);
    glBindRenderbuffer(GL_RENDERBUFFER,depth);glRenderbufferStorage(GL_RENDERBUFFER,GL_DEPTH24_STENCIL8,2,2);
    glFramebufferRenderbuffer(GL_FRAMEBUFFER,GL_DEPTH_STENCIL_ATTACHMENT,GL_RENDERBUFFER,depth);
    GLenum none=GL_NONE;glDrawBuffers(1,&none);glReadBuffer(GL_NONE);
    bool complete=glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE;
    glStencilMask(255);glClearStencil(173);glClear(GL_STENCIL_BUFFER_BIT);
    glBindTexture(GL_TEXTURE_2D,tex[1]);glTexStorage2D(GL_TEXTURE_2D,1,GL_DEPTH24_STENCIL8,2,2);
    glTexParameteri(GL_TEXTURE_2D,0x90EA /* DEPTH_STENCIL_TEXTURE_MODE */,0x1901 /* STENCIL_INDEX */);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
    glBindFramebuffer(GL_DRAW_FRAMEBUFFER,fb[1]);glFramebufferTexture2D(GL_DRAW_FRAMEBUFFER,GL_DEPTH_STENCIL_ATTACHMENT,GL_TEXTURE_2D,tex[1],0);
    glDrawBuffers(1,&none);complete=complete&&glCheckFramebufferStatus(GL_DRAW_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE;
    glBlitFramebuffer(0,0,2,2,0,0,2,2,GL_STENCIL_BUFFER_BIT,GL_NEAREST);
    GLenum copied=glGetError();
    glBindFramebuffer(GL_FRAMEBUFFER,fb[2]);glBindTexture(GL_TEXTURE_2D,tex[2]);glTexStorage2D(GL_TEXTURE_2D,1,GL_RGBA8,2,2);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,tex[2],0);
    const char* source[]={"#version 300 es\nvoid main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.-1.,0.,1.);}",
        "#version 300 es\nprecision highp float;precision highp usampler2D;uniform usampler2D s;out vec4 c;void main(){uint v=texelFetch(s,ivec2(gl_FragCoord.xy),0).r;c=vec4(float(v)/255.,0.,0.,1.);}"};
    program=glCreateProgram();bool compiled=true;
    for(int i=0;i<2;++i){shaders[i]=glCreateShader(i?GL_FRAGMENT_SHADER:GL_VERTEX_SHADER);glShaderSource(shaders[i],1,&source[i],nullptr);glCompileShader(shaders[i]);GLint ok=0;glGetShaderiv(shaders[i],GL_COMPILE_STATUS,&ok);compiled=compiled&&ok;glAttachShader(program,shaders[i]);}
    glLinkProgram(program);GLint linked=0;glGetProgramiv(program,GL_LINK_STATUS,&linked);
    glUseProgram(program);glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,tex[1]);glUniform1i(glGetUniformLocation(program,"s"),0);
    glViewport(0,0,2,2);glDrawArrays(GL_TRIANGLES,0,3);
    uint8_t pixels[16]{};glReadPixels(0,0,2,2,GL_RGBA,GL_UNSIGNED_BYTE,pixels);GLenum sampled=glGetError();
    bool valid=complete&&compiled&&linked&&copied==GL_NO_ERROR&&sampled==GL_NO_ERROR;
    for(int i=0;i<4;++i)valid=valid&&pixels[4*i]==173&&pixels[4*i+3]==255;
    glBindFramebuffer(GL_FRAMEBUFFER,0);glUseProgram(0);glDeleteProgram(program);for(auto s:shaders)glDeleteShader(s);
    glDeleteRenderbuffers(1,&depth);glDeleteTextures(3,tex);glDeleteFramebuffers(3,fb);
    return std::string("{\"lossless_copy_and_sample\":")+(valid?"true":"false")+",\"copy_error\":"+std::to_string(copied)+",\"sample_error\":"+std::to_string(sampled)+",\"sample\":"+std::to_string(pixels[0])+"}";
}

// Exercise every stencil byte through the exact integer-transfer shaders.
static std::string StencilIntegerProbe() {
    while(glGetError()!=GL_NO_ERROR){}
    GLuint fb[3]{},tex[2]{},depth=0,program=0,vao=0;
    glGenFramebuffers(3,fb);glGenTextures(2,tex);glGenRenderbuffers(1,&depth);
    glBindFramebuffer(GL_FRAMEBUFFER,fb[0]);glBindRenderbuffer(GL_RENDERBUFFER,depth);
    glRenderbufferStorage(GL_RENDERBUFFER,GL_DEPTH24_STENCIL8,16,16);
    glFramebufferRenderbuffer(GL_FRAMEBUFFER,GL_DEPTH_STENCIL_ATTACHMENT,GL_RENDERBUFFER,depth);
    GLenum none=GL_NONE;glDrawBuffers(1,&none);glReadBuffer(GL_NONE);
    bool complete=glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE;
    glStencilMask(255);glEnable(GL_SCISSOR_TEST);
    for(int i=0;i<256;++i){glScissor(i%16,i/16,1,1);glClearStencil(i);glClear(GL_STENCIL_BUFFER_BIT);}
    glDisable(GL_SCISSOR_TEST);
    glBindTexture(GL_TEXTURE_2D,tex[0]);glTexStorage2D(GL_TEXTURE_2D,1,GL_DEPTH24_STENCIL8,16,16);
    glTexParameteri(GL_TEXTURE_2D,0x90EA,0x1901);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
    glBindFramebuffer(GL_DRAW_FRAMEBUFFER,fb[1]);glFramebufferTexture2D(GL_DRAW_FRAMEBUFFER,GL_DEPTH_STENCIL_ATTACHMENT,GL_TEXTURE_2D,tex[0],0);glDrawBuffers(1,&none);
    complete=complete&&glCheckFramebufferStatus(GL_DRAW_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE;
    glBlitFramebuffer(0,0,16,16,0,0,16,16,GL_STENCIL_BUFFER_BIT,GL_NEAREST);
    GLenum copied=glGetError();
    glBindFramebuffer(GL_FRAMEBUFFER,fb[2]);glBindTexture(GL_TEXTURE_2D,tex[1]);glTexStorage2D(GL_TEXTURE_2D,1,GL_R8UI,16,16);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,tex[1],0);
    GLenum color=GL_COLOR_ATTACHMENT0;glDrawBuffers(1,&color);glReadBuffer(color);
    complete=complete&&glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE;
    program=glCreateProgram();bool compiled=true;
    for(unsigned i=0;i<2;++i){GLuint shader=glCreateShader(i?GL_FRAGMENT_SHADER:GL_VERTEX_SHADER);auto text=DiscoStencilPrograms::codes[i];glShaderSource(shader,1,&text,nullptr);glCompileShader(shader);GLint ok=0;glGetShaderiv(shader,GL_COMPILE_STATUS,&ok);compiled=compiled&&ok;glAttachShader(program,shader);glDeleteShader(shader);}
    glLinkProgram(program);GLint linked=0;glGetProgramiv(program,GL_LINK_STATUS,&linked);
    glGenVertexArrays(1,&vao);glBindVertexArray(vao);glUseProgram(program);glActiveTexture(GL_TEXTURE0);glBindSampler(0,0);glBindTexture(GL_TEXTURE_2D,tex[0]);glUniform1i(glGetUniformLocation(program,"s"),0);
    glDisable(GL_BLEND);glDisable(GL_DEPTH_TEST);glDisable(GL_STENCIL_TEST);glDisable(GL_CULL_FACE);glColorMask(1,1,1,1);glViewport(0,0,16,16);glDrawArrays(GL_TRIANGLES,0,3);
    GLuint pixels[256*4]{};glReadPixels(0,0,16,16,GL_RGBA_INTEGER,GL_UNSIGNED_INT,pixels);GLenum sampled=glGetError();
    unsigned matches=0;for(unsigned i=0;i<256;++i)if(pixels[4*i]==i)++matches;
    bool valid=complete&&compiled&&linked&&copied==GL_NO_ERROR&&sampled==GL_NO_ERROR&&matches==256;
    glDeleteTextures(1,&tex[1]);glGenTextures(1,&tex[1]);glBindTexture(GL_TEXTURE_2D,tex[1]);glTexStorage2D(GL_TEXTURE_2D,1,GL_RGBA8,16,16);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,tex[1],0);
    glUseProgram(0);glDeleteProgram(program);program=glCreateProgram();bool paletteCompiled=true;
    for(unsigned i=0;i<2;++i){GLuint shader=glCreateShader(i?GL_FRAGMENT_SHADER:GL_VERTEX_SHADER);auto text=i?DiscoStencilPrograms::paletteFragment:DiscoStencilPrograms::codes[0];glShaderSource(shader,1,&text,nullptr);glCompileShader(shader);GLint ok=0;glGetShaderiv(shader,GL_COMPILE_STATUS,&ok);paletteCompiled=paletteCompiled&&ok;glAttachShader(program,shader);glDeleteShader(shader);}
    glLinkProgram(program);GLint paletteLinked=0;glGetProgramiv(program,GL_LINK_STATUS,&paletteLinked);glUseProgram(program);
    uint8_t expected[64]{};float palette[64]{};
    for(unsigned i=1;i<16;++i){expected[4*i]=i*11;expected[4*i+1]=255-i*7;expected[4*i+2]=i*13;expected[4*i+3]=255;}
    for(unsigned j=0;j<4;++j)expected[4*8+j]=255;
    for(unsigned j=0;j<64;++j)palette[j]=expected[j]/255.f;
    glUniform4fv(glGetUniformLocation(program,"palette[0]"),16,palette);glUniform2i(glGetUniformLocation(program,"targetSize"),16,16);
    glBindTexture(GL_TEXTURE_2D,tex[0]);glUniform1i(glGetUniformLocation(program,"s"),0);glDisable(GL_DITHER);glDrawArrays(GL_TRIANGLES,0,3);
    uint8_t palettePixels[256*4]{};glReadPixels(0,0,16,16,GL_RGBA,GL_UNSIGNED_BYTE,palettePixels);GLenum paletteError=glGetError();
    unsigned paletteMatches=0;for(unsigned i=0;i<256;++i){bool equal=true;for(unsigned j=0;j<4;++j)equal=equal&&palettePixels[4*i+j]==expected[4*(i&15)+j];if(equal)++paletteMatches;}
    bool paletteValid=paletteCompiled&&paletteLinked&&!paletteError&&paletteMatches==256;
    glBindFramebuffer(GL_FRAMEBUFFER,0);glUseProgram(0);glBindVertexArray(0);glDeleteProgram(program);glDeleteVertexArrays(1,&vao);glDeleteRenderbuffers(1,&depth);glDeleteTextures(2,tex);glDeleteFramebuffers(3,fb);
    return std::string("{\"all_256_bytes_preserved\":")+(valid?"true":"false")+",\"matching_bytes\":"+std::to_string(matches)+",\"copy_error\":"+std::to_string(copied)+",\"sample_error\":"+std::to_string(sampled)+",\"palette_all_256_pixels_preserved\":"+(paletteValid?"true":"false")+",\"palette_matching_pixels\":"+std::to_string(paletteMatches)+",\"palette_error\":"+std::to_string(paletteError)+"}";
}
