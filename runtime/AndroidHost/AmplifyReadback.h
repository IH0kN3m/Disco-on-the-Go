// Original GLES readback adapter for the supplied CPU-only Amplify plugin.
#pragma once
#include <GLES3/gl3.h>
#include <memory>
#include <mutex>
#include <unordered_map>
#include <vector>
#include <cstring>
#include <android/log.h>
#include <cstdlib>
#include "ReadbackPolicy.h"
namespace DiscoAmplifyReadback {
struct State {
    GLuint texture;int width,height;
    std::vector<uint8_t> pixels;
    std::mutex lock;
    bool queued=false,ready=false,retired=false;
};
static std::mutex lock;
static std::unordered_map<void*,std::shared_ptr<State>> owned;
static std::vector<std::shared_ptr<State>> pending;
[[noreturn]] static void Fail(const char* message) {
    __android_log_print(ANDROID_LOG_FATAL,"DiscoRuntime","Amplify GLES readback: %s",message);std::abort();
}
static std::shared_ptr<State> Find(void* handle) {
    auto it=owned.find(handle);if(it==owned.end())Fail("unknown ownership handle");return it->second;
}
static void* Create(void* texture,int width,int height) {
    size_t bytes=0;
    if(!texture||uintptr_t(texture)>UINT32_MAX||!DiscoReadbackPolicy::Shape(width,height,bytes))Fail("unsupported readback dimensions/texture");
    std::lock_guard<std::mutex> guard(lock);if(owned.size()>=64)Fail("readback ownership limit");
    size_t used=0;for(auto& entry:owned)used+=entry.second->pixels.size();
    if(bytes>DiscoReadbackPolicy::Budget-used)Fail("readback memory budget");
    auto state=std::make_shared<State>();state->texture=GLuint(uintptr_t(texture));state->width=width;state->height=height;
    state->pixels.resize(bytes);
    void* handle=state.get();owned.emplace(handle,state);
    __android_log_print(ANDROID_LOG_INFO,"DiscoRuntime","Amplify GLES readback created %dx%d",width,height);return handle;
}
static void Destroy(void* handle) {
    if(!handle)return;
    std::lock_guard<std::mutex> guard(lock);auto state=Find(handle);
    {std::lock_guard<std::mutex> stateGuard(state->lock);state->retired=true;}
    owned.erase(handle);
}
static void Issue(void* handle) {
    std::lock_guard<std::mutex> guard(lock);auto state=Find(handle);
    if(!state->queued){state->queued=true;pending.push_back(state);}
}
static void Pixels(void* handle,void* destination) {
    if(!destination)Fail("null destination");
    std::shared_ptr<State> state;
    {std::lock_guard<std::mutex> guard(lock);state=Find(handle);}
    std::lock_guard<std::mutex> guard(state->lock);std::memcpy(destination,state->pixels.data(),state->pixels.size());
}
static void Render(int event) {
    if(event!=0)Fail("unexpected render event");
    std::vector<std::shared_ptr<State>> work;
    {std::lock_guard<std::mutex> guard(lock);work.swap(pending);for(auto& state:work)state->queued=false;}
    GLint read,readBuffer,packBuffer,alignment,rowLength,skipRows,skipPixels;
    glGetIntegerv(GL_READ_FRAMEBUFFER_BINDING,&read);glGetIntegerv(GL_READ_BUFFER,&readBuffer);
    glGetIntegerv(GL_PIXEL_PACK_BUFFER_BINDING,&packBuffer);glGetIntegerv(GL_PACK_ALIGNMENT,&alignment);
    glGetIntegerv(GL_PACK_ROW_LENGTH,&rowLength);glGetIntegerv(GL_PACK_SKIP_ROWS,&skipRows);glGetIntegerv(GL_PACK_SKIP_PIXELS,&skipPixels);
    glBindBuffer(GL_PIXEL_PACK_BUFFER,0);glPixelStorei(GL_PACK_ALIGNMENT,1);glPixelStorei(GL_PACK_ROW_LENGTH,0);
    glPixelStorei(GL_PACK_SKIP_ROWS,0);glPixelStorei(GL_PACK_SKIP_PIXELS,0);
    GLuint framebuffer=0;glGenFramebuffers(1,&framebuffer);glBindFramebuffer(GL_READ_FRAMEBUFFER,framebuffer);glReadBuffer(GL_COLOR_ATTACHMENT0);
    for(auto& state:work){
        std::lock_guard<std::mutex> guard(state->lock);if(state->retired)continue;
        glFramebufferTexture2D(GL_READ_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,state->texture,0);
        if(glCheckFramebufferStatus(GL_READ_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)Fail("incomplete source framebuffer");
        glReadPixels(0,0,state->width,state->height,GL_RGBA,GL_UNSIGNED_BYTE,state->pixels.data());
        if(glGetError()!=GL_NO_ERROR)Fail("pixel transfer failed");
        if(!state->ready){
            size_t nonzero=0;uint32_t first=0;
            for(size_t i=0;i<state->pixels.size();i+=4){uint32_t pixel;std::memcpy(&pixel,state->pixels.data()+i,4);if(pixel){++nonzero;if(!first)first=pixel;}}
            __android_log_print(ANDROID_LOG_INFO,"DiscoRuntime","Amplify GLES feedback read %dx%d nonzero=%zu first=%08x",state->width,state->height,nonzero,first);
        }
        state->ready=true;
    }
    glBindFramebuffer(GL_READ_FRAMEBUFFER,read);glReadBuffer(readBuffer);glDeleteFramebuffers(1,&framebuffer);
    glBindBuffer(GL_PIXEL_PACK_BUFFER,packBuffer);glPixelStorei(GL_PACK_ALIGNMENT,alignment);glPixelStorei(GL_PACK_ROW_LENGTH,rowLength);
    glPixelStorei(GL_PACK_SKIP_ROWS,skipRows);glPixelStorei(GL_PACK_SKIP_PIXELS,skipPixels);
}
static void* Event() {return reinterpret_cast<void*>(&Render);}
static void* Symbol(const char* name) {
    if(!std::strcmp(name,"CreatePrePassReadback"))return reinterpret_cast<void*>(&Create);
    if(!std::strcmp(name,"DestroyPrePassReadback"))return reinterpret_cast<void*>(&Destroy);
    if(!std::strcmp(name,"IssuePrePassRead"))return reinterpret_cast<void*>(&Issue);
    if(!std::strcmp(name,"GetPrePassPixels"))return reinterpret_cast<void*>(&Pixels);
    if(!std::strcmp(name,"GetRenderEventFunc"))return reinterpret_cast<void*>(&Event);
    return nullptr;
}
}
