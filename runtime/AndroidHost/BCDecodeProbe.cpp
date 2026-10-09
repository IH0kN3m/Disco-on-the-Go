// Original GLES compute experiment: decode bounded synthetic BC1/BC3 blocks.
// No texture residency policy or Unity upload integration is implemented here.
#include <GLES3/gl31.h>
#include <cstdint>
#include <cstring>
#include <string>
#include <sstream>
#include "BCBlock.h"

std::string DiscoBCDecodeReport() {
    const char* source=R"GLSL(#version 310 es
precision highp int;
layout(local_size_x=64) in;
layout(std430,binding=0) readonly buffer Source { uint blocks[]; };
layout(std430,binding=1) writeonly buffer Destination { uint pixels[]; };
uniform uint mode;
uniform uint blockCount;
uint color(uint v) {
    uint r=v>>11,g=(v>>5)&63u,b=v&31u;
    return (r<<3|r>>2)|((g<<2|g>>4)<<8)|((b<<3|b>>2)<<16)|0xff000000u;
}
uint mixColor(uint a,uint b,uint aw,uint bw,uint divisor) {
    uint result=0xff000000u;
    for(uint shift=0u;shift<24u;shift+=8u)
        result|=((aw*((a>>shift)&255u)+bw*((b>>shift)&255u))/divisor)<<shift;
    return result;
}
void main() {
    uint n=gl_GlobalInvocationID.x;
    if(n>=16u*blockCount)return;
    uint block=n/16u,pixel=n%16u,stride=mode==0u?2u:4u;
    uint offset=block*stride+(mode==0u?0u:2u);
    uint pair=blocks[offset],a=pair&65535u,b=pair>>16;
    uint first=color(a),second=color(b),selector=(blocks[offset+1u]>>(2u*pixel))&3u;
    uint value;
    if(selector==0u)value=first;
    else if(selector==1u)value=second;
    else if(mode!=0u || a>b)value=selector==2u?mixColor(first,second,2u,1u,3u):mixColor(first,second,1u,2u,3u);
    else value=selector==2u?mixColor(first,second,1u,1u,2u):0u;
    if(mode!=0u) {
        uint low=blocks[block*4u],high=blocks[block*4u+1u];
        uint alpha0=low&255u,alpha1=(low>>8)&255u;
        uint bits=16u+3u*pixel;
        uint index=bits>=32u?(high>>(bits-32u))&7u:((low>>bits)|(bits>29u?high<<(32u-bits):0u))&7u;
        uint alpha;
        if(index<2u)alpha=index==0u?alpha0:alpha1;
        else if(alpha0>alpha1)alpha=((8u-index)*alpha0+(index-1u)*alpha1)/7u;
        else if(index<6u)alpha=((6u-index)*alpha0+(index-1u)*alpha1)/5u;
        else alpha=index==6u?0u:255u;
        value=(value&0xffffffu)|(alpha<<24);
    }
    pixels[n]=value;
}
)GLSL";
    GLuint shader=glCreateShader(GL_COMPUTE_SHADER);glShaderSource(shader,1,&source,nullptr);glCompileShader(shader);
    GLint valid=0;glGetShaderiv(shader,GL_COMPILE_STATUS,&valid);
    if(!valid){glDeleteShader(shader);return "{\"error\":\"compute shader compilation failed\"}";}
    GLuint program=glCreateProgram();glAttachShader(program,shader);glLinkProgram(program);glDeleteShader(shader);
    glGetProgramiv(program,GL_LINK_STATUS,&valid);
    if(!valid){glDeleteProgram(program);return "{\"error\":\"compute link failed\"}";}
    GLuint buffers[2];glGenBuffers(2,buffers);glUseProgram(program);
    unsigned mismatch=0,compared=0;
    for(unsigned mode=0;mode<2;++mode) {
        // Deterministic synthetic blocks exercise endpoint ordering and packed
        // alpha selectors crossing the 32-bit word boundary, never game data.
        uint8_t input[64*16]={};uint32_t expected[64*16],seed=0x2468ace1u;
        unsigned stride=mode?16:8;
        for(unsigned i=0;i<64*stride;++i){seed=seed*1664525u+1013904223u;input[i]=seed>>24;}
        for(unsigned block=0;block<64;++block) DiscoBC::Decode(input+block*stride,stride,mode,expected+block*16,16);
        glBindBuffer(GL_SHADER_STORAGE_BUFFER,buffers[0]);glBufferData(GL_SHADER_STORAGE_BUFFER,64*stride,input,GL_STATIC_DRAW);
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER,0,buffers[0]);
        glBindBuffer(GL_SHADER_STORAGE_BUFFER,buffers[1]);glBufferData(GL_SHADER_STORAGE_BUFFER,sizeof(expected),nullptr,GL_DYNAMIC_READ);
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER,1,buffers[1]);
        glUniform1ui(glGetUniformLocation(program,"mode"),mode);
        glUniform1ui(glGetUniformLocation(program,"blockCount"),64);
        glDispatchCompute(16,1,1);glMemoryBarrier(GL_BUFFER_UPDATE_BARRIER_BIT);
        const uint32_t* result=static_cast<const uint32_t*>(glMapBufferRange(GL_SHADER_STORAGE_BUFFER,0,sizeof(expected),GL_MAP_READ_BIT));
        if(!result) mismatch+=1024;
        else {for(unsigned i=0;i<1024;++i) mismatch+=result[i]!=expected[i];glUnmapBuffer(GL_SHADER_STORAGE_BUFFER);}
        compared+=1024;
    }
    GLenum error=glGetError();glUseProgram(0);glDeleteBuffers(2,buffers);glDeleteProgram(program);
    std::ostringstream result;
    result<<"{\"formats\":[\"BC1\",\"BC3\"],\"pixels_compared\":"<<compared<<",\"mismatches\":"<<mismatch
          <<",\"gl_error\":"<<error<<",\"passed\":"<<(!mismatch && error==GL_NO_ERROR?"true":"false")
          <<",\"scope\":\"Synthetic GPU-to-reference decode test; BC6H/BC7, streaming and rendered fidelity pending\"}";
    return result.str();
}
