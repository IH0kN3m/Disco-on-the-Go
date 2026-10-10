// Lossless GPU transfer from sampled D24S8/D32S8 stencil into R8_UInt.
#pragma once
#include "StencilPrograms.h"
namespace DiscoStencilResolve {
static GLuint programs[2]{},vao=0;
static void Draw(GLuint source,GLuint destination,GLuint& framebuffer,int width,int height,const float* palette=nullptr) {
    GLuint& program=programs[palette?1:0];
    GLenum prior=glGetError();
    GLint read,draw,previousProgram,previousVao,texture,sampler,unit,viewport[4];
    glGetIntegerv(GL_READ_FRAMEBUFFER_BINDING,&read);glGetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING,&draw);
    glGetIntegerv(GL_CURRENT_PROGRAM,&previousProgram);glGetIntegerv(GL_VERTEX_ARRAY_BINDING,&previousVao);
    glGetIntegerv(GL_ACTIVE_TEXTURE,&unit);glGetIntegerv(GL_TEXTURE_BINDING_2D,&texture);glGetIntegerv(GL_SAMPLER_BINDING,&sampler);glGetIntegerv(GL_VIEWPORT,viewport);
    GLboolean mask[4];glGetBooleanv(GL_COLOR_WRITEMASK,mask);
    const GLenum caps[]={GL_BLEND,GL_CULL_FACE,GL_DEPTH_TEST,GL_STENCIL_TEST,GL_SCISSOR_TEST,GL_RASTERIZER_DISCARD};
    GLboolean enabled[6];for(unsigned i=0;i<6;++i){enabled[i]=glIsEnabled(caps[i]);glDisable(caps[i]);}
    if(!program){
        const auto& codes=DiscoStencilPrograms::codes;
        program=glCreateProgram();for(unsigned i=0;i<2;++i){GLuint shader=glCreateShader(i?GL_FRAGMENT_SHADER:GL_VERTEX_SHADER);auto code=(i&&palette)?DiscoStencilPrograms::paletteFragment:codes[i];glShaderSource(shader,1,&code,nullptr);glCompileShader(shader);GLint ok;glGetShaderiv(shader,GL_COMPILE_STATUS,&ok);if(!ok)DiscoSceneResidency::Fail("stencil integer resolve shader");glAttachShader(program,shader);glDeleteShader(shader);}
        glLinkProgram(program);GLint linked;glGetProgramiv(program,GL_LINK_STATUS,&linked);if(!linked)DiscoSceneResidency::Fail("stencil integer resolve link");
        if(!vao)glGenVertexArrays(1,&vao);
    }
    if(!framebuffer)glGenFramebuffers(1,&framebuffer);
    glBindFramebuffer(GL_DRAW_FRAMEBUFFER,framebuffer);glFramebufferTexture2D(GL_DRAW_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,destination,0);
    GLenum color=GL_COLOR_ATTACHMENT0;glDrawBuffers(1,&color);
    if(glCheckFramebufferStatus(GL_DRAW_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)DiscoSceneResidency::Fail("stencil integer render target");
    GLint component=0,bits=0;glGetFramebufferAttachmentParameteriv(GL_DRAW_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_FRAMEBUFFER_ATTACHMENT_COMPONENT_TYPE,&component);glGetFramebufferAttachmentParameteriv(GL_DRAW_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_FRAMEBUFFER_ATTACHMENT_RED_SIZE,&bits);
    glUseProgram(program);glBindVertexArray(vao);glBindSampler(unit-GL_TEXTURE0,0);glBindTexture(GL_TEXTURE_2D,source);
    glUniform1i(glGetUniformLocation(program,"s"),unit-GL_TEXTURE0);glViewport(0,0,width,height);glColorMask(1,1,1,1);
    if(palette){glUniform4fv(glGetUniformLocation(program,"palette[0]"),16,palette);glUniform2i(glGetUniformLocation(program,"targetSize"),width,height);}
    GLenum setup=glGetError();glDrawArrays(GL_TRIANGLES,0,3);GLenum error=glGetError();
    glBindFramebuffer(GL_READ_FRAMEBUFFER,read);glBindFramebuffer(GL_DRAW_FRAMEBUFFER,draw);glUseProgram(previousProgram);glBindVertexArray(previousVao);
    glBindTexture(GL_TEXTURE_2D,texture);glBindSampler(unit-GL_TEXTURE0,sampler);glViewport(viewport[0],viewport[1],viewport[2],viewport[3]);glColorMask(mask[0],mask[1],mask[2],mask[3]);
    for(unsigned i=0;i<6;++i)if(enabled[i])glEnable(caps[i]);
    static unsigned reports[2]{};if(reports[palette?1:0]++<8)DiscoSceneResidency::Log("Stencil resolve palette=%d prior=%u setup=%u draw=%u source=%u target=%u unit=%d component=%x bits=%d\n",palette!=nullptr,prior,setup,error,source,destination,unit-GL_TEXTURE0,component,bits);
}
}
