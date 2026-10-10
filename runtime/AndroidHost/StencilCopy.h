// Preserve the game's sampled stencil mask on GLES without texture views.
#pragma once
#include <GLES3/gl3.h>
#include <atomic>
#include <mutex>
#include "StencilResolve.h"
namespace DiscoStencil {
using namespace DiscoSceneResidency;
struct State {
    uint32_t target=0,camera=0,commands=0,external=0;
    int width=0,height=0,property=0,event=11;
    bool hasProperty=false,bound=false;
    GLuint texture=0,framebuffer=0,resolvedFramebuffer=0,colorFramebuffer=0;
    struct Palette {GLuint target=0;int width=0,height=0;float colors[64]{};} palette;
    std::mutex paletteLock;
    std::atomic<bool> mali{false};
    std::atomic<GLuint> resolvedTexture{0};
    std::atomic<bool> ready{false};
    std::atomic<bool> retired{false};
};
static std::vector<State*> states;
static State* activeState=nullptr;
static std::vector<State*> garbage;
static std::mutex garbageLock;
template<class F> static F Icall(const char* name) {
    auto value=il2cpp_resolve_icall(name);if(!value)Fail(name);return reinterpret_cast<F>(value);
}
static Il2CppObject* Object(uint32_t handle) { return handle?il2cpp_gchandle_get_target(handle):nullptr; }
static bool Alive(Il2CppObject* object) {
    if(!object)return false;
    void* args[]={object};
    return Boolean(Call(Class("UnityEngine.CoreModule.dll","UnityEngine","Object"),"op_Implicit",1,nullptr,args));
}
static State* Find(void* target) { for(auto* s:states)if(!s->retired.load()&&Object(s->target)==target)return s;return nullptr; }
static void Drain(int) {
    std::lock_guard<std::mutex> lock(garbageLock);
    for(auto* s:garbage){if(s->texture)glDeleteTextures(1,&s->texture);if(s->framebuffer)glDeleteFramebuffers(1,&s->framebuffer);if(s->resolvedFramebuffer)glDeleteFramebuffers(1,&s->resolvedFramebuffer);if(s->colorFramebuffer)glDeleteFramebuffers(1,&s->colorFramebuffer);s->texture=s->framebuffer=s->resolvedFramebuffer=0;}
    garbage.clear();
}
static void Retire(State* state) {
    if(state->retired.exchange(true))return;
    if(auto* camera=Object(state->camera);Alive(camera))
        Icall<void(*)(void*,int,void*)>("UnityEngine.Camera::RemoveCommandBufferImpl")(camera,state->event,Object(state->commands));
    if(auto* external=Object(state->external)){
        void* args[]={external};Call(Class("UnityEngine.CoreModule.dll","UnityEngine","Object"),"Destroy",1,nullptr,args);
    }
    if(auto* commands=Object(state->commands))Call(Class("UnityEngine.CoreModule.dll","UnityEngine.Rendering","CommandBuffer"),"Dispose",0,commands,nullptr);
    for(auto* handle:{&state->target,&state->camera,&state->commands,&state->external}){if(*handle)il2cpp_gchandle_free(*handle);*handle=0;}
    {std::lock_guard<std::mutex> lock(garbageLock);garbage.push_back(state);}
    Icall<void(*)(void*,int)>("UnityEngine.GL::GLIssuePluginEvent")(reinterpret_cast<void*>(&Drain),0);
}
static void Detach(void* camera,void* next) {
    for(auto* state:states)if(!state->retired.load()&&Object(state->camera)==camera&&Object(state->target)!=next)Retire(state);
}
static void Copy(int,void* data) {
    auto* state=static_cast<State*>(data);
    if(state->retired.load())return;
    GLint read=0,draw=0,texture=0,depth=0,stencil=0;
    glGetIntegerv(GL_READ_FRAMEBUFFER_BINDING,&read);glGetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING,&draw);
    glGetIntegerv(GL_TEXTURE_BINDING_2D,&texture);
    if(!draw)return;
    glGetFramebufferAttachmentParameteriv(GL_DRAW_FRAMEBUFFER,GL_DEPTH_ATTACHMENT,GL_FRAMEBUFFER_ATTACHMENT_DEPTH_SIZE,&depth);
    glGetFramebufferAttachmentParameteriv(GL_DRAW_FRAMEBUFFER,GL_STENCIL_ATTACHMENT,GL_FRAMEBUFFER_ATTACHMENT_STENCIL_SIZE,&stencil);
    if((depth!=24&&depth!=32)||stencil!=8)return;
    if(!state->texture){
        state->mali=std::strstr(reinterpret_cast<const char*>(glGetString(GL_RENDERER)),"Mali")!=nullptr;
        glGenTextures(1,&state->texture);glBindTexture(GL_TEXTURE_2D,state->texture);
        glTexStorage2D(GL_TEXTURE_2D,1,depth==24?GL_DEPTH24_STENCIL8:GL_DEPTH32F_STENCIL8,state->width,state->height);
        glTexParameteri(GL_TEXTURE_2D,0x90EA,0x1901); // Sample stencil from depth/stencil storage.
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
        glGenFramebuffers(1,&state->framebuffer);glBindFramebuffer(GL_DRAW_FRAMEBUFFER,state->framebuffer);
        glFramebufferTexture2D(GL_DRAW_FRAMEBUFFER,GL_DEPTH_STENCIL_ATTACHMENT,GL_TEXTURE_2D,state->texture,0);
        GLenum none=GL_NONE;glDrawBuffers(1,&none);
        if(glCheckFramebufferStatus(GL_DRAW_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)Fail("stencil copy framebuffer incomplete");
        Log("GLES stencil copy allocated %dx%d depth=%d stencil=%d\n",state->width,state->height,depth,stencil);
    }
    GLboolean scissor=glIsEnabled(GL_SCISSOR_TEST);if(scissor)glDisable(GL_SCISSOR_TEST);
    glBindFramebuffer(GL_READ_FRAMEBUFFER,draw);glBindFramebuffer(GL_DRAW_FRAMEBUFFER,state->framebuffer);
    glBlitFramebuffer(0,0,state->width,state->height,0,0,state->width,state->height,GL_STENCIL_BUFFER_BIT,GL_NEAREST);
    GLenum error=glGetError();
    glBindFramebuffer(GL_READ_FRAMEBUFFER,read);glBindFramebuffer(GL_DRAW_FRAMEBUFFER,draw);
    glBindTexture(GL_TEXTURE_2D,texture);if(scissor)glEnable(GL_SCISSOR_TEST);
    if(error!=GL_NO_ERROR){Log("GLES stencil copy error=%u\n",error);return;}
    if(GLuint resolved=state->resolvedTexture.load(std::memory_order_acquire))DiscoStencilResolve::Draw(state->texture,resolved,state->resolvedFramebuffer,state->width,state->height);
    state->ready.store(true,std::memory_order_release);

}
static bool Request(void* target,int format) {
    if(format!=13)return false;
    if(!Find(target)){
        // Callback records stay address-stable for already queued render work.
        // Their GPU resources and managed handles are released on retirement.
        if(states.size()>=4096)Fail("stencil callback lifetime limit");
        auto* state=new State;state->target=il2cpp_gchandle_new(static_cast<Il2CppObject*>(target),false);
        states.push_back(state);
    }
    return true;
}
static void Attach(void* camera,void* target) {
    auto* state=Find(target);if(!state||state->commands)return;
    state->width=Icall<int(*)(void*)>("UnityEngine.RenderTexture::get_width")(target);
    state->height=Icall<int(*)(void*)>("UnityEngine.RenderTexture::get_height")(target);
    if(state->width<=0||state->height<=0||state->width>16384||state->height>16384)Fail("stencil target dimensions");
    auto* klass=Class("UnityEngine.CoreModule.dll","UnityEngine.Rendering","CommandBuffer");
    auto* commands=il2cpp_object_new(klass);state->commands=il2cpp_gchandle_new(commands,false);
    Call(klass,".ctor",0,commands,nullptr);
    Icall<void(*)(void*,void*,int,void*)>("UnityEngine.Rendering.CommandBuffer::IssuePluginEventAndDataInternal")
        (commands,reinterpret_cast<void*>(&Copy),0,state);
    int event=-1;
    auto* events=Class("UnityEngine.CoreModule.dll","UnityEngine.Rendering","CameraEvent");
    // OutlineLayer consumes stencil at BeforeForwardAlpha (16). Copy while
    // the scene's stencil attachment is still bound, before that consumer.
    // AfterEverything sees post-processing targets and runs too late.
    auto* field=il2cpp_class_get_field_from_name(events,"AfterForwardOpaque");if(!field)Fail("camera event ABI");
    il2cpp_field_static_get_value(field,&event);if(event!=11)Fail("camera event differs from pinned ABI");
    state->event=event;
    Icall<void(*)(void*,int,void*)>("UnityEngine.Camera::AddCommandBufferImpl")(camera,event,commands);
    state->camera=il2cpp_gchandle_new(static_cast<Il2CppObject*>(camera),false);
    Log("GLES stencil copy attached %dx%d event=%d\n",state->width,state->height,event);
}
static bool Bind(int property,void* target,int element) {
    auto* state=Find(target);if(!state||element!=2)return false;
    if(!state->hasProperty){
        int expected=Icall<int(*)(Il2CppString*)>("UnityEngine.Shader::PropertyToID")(il2cpp_string_new("_CameraDepthStencilTexture"));
        Log("Stencil global property supplied=%d expected=%d\n",property,expected);
    }
    state->property=property;state->hasProperty=true;activeState=state;return true;
}
// Mali's Unity 2020 unsigned-sampler color pass drops valid IDs. Keep the
// original palette and final edge effect, replacing just the color lookup.
static void PaletteDraw(int,void* data) {
    auto* state=static_cast<State*>(data);if(state->retired.load()||!state->mali.load())return;
    State::Palette snapshot;
    {std::lock_guard<std::mutex> guard(state->paletteLock);snapshot=state->palette;}
    if(snapshot.target&&state->texture)DiscoStencilResolve::Draw(state->texture,snapshot.target,state->colorFramebuffer,snapshot.width,snapshot.height,snapshot.colors);
}
static void UpdatePalette(State* state) {
    if(!state->mali.load())return;
    auto* outline=Class("Assembly-CSharp.dll","","OutlineLayer");
    Il2CppObject* target=nullptr;Il2CppObject* material=nullptr;
    for(auto pair:{std::pair<const char*,Il2CppObject**>{"outlineColorRT",&target},{"outlineColorMat",&material}}){
        auto* field=il2cpp_class_get_field_from_name(outline,pair.first);if(!field||!(il2cpp_field_get_flags(field)&0x10))Fail("outline palette field ABI");
        il2cpp_field_static_get_value(field,pair.second);
    }
    if(!Alive(target)||!Alive(material))return;
    State::Palette snapshot;
    snapshot.width=Icall<int(*)(void*)>("UnityEngine.RenderTexture::get_width")(target);
    snapshot.height=Icall<int(*)(void*)>("UnityEngine.RenderTexture::get_height")(target);
    if(snapshot.width<=0||snapshot.height<=0||snapshot.width>16384||snapshot.height>16384)Fail("outline palette dimensions");
    uintptr_t native=uintptr_t(Icall<void*(*)(void*)>("UnityEngine.Texture::GetNativeTexturePtr")(target));
    if(!native||native>UINT32_MAX)Fail("outline palette texture ownership");snapshot.target=GLuint(native);
    const char* names[]={nullptr,"_Sense","_Int","_Psy","_Fys","_Mot","_Pry","_Inactive",nullptr,"_AutoSense","_AutoInt","_AutoPsy","_AutoFys","_AutoMot","_AutoPry","_AutoInactive"};
    static int ids[16]{};
    for(unsigned i=1;i<16;++i){
        if(!names[i]){for(unsigned j=0;j<4;++j)snapshot.colors[4*i+j]=1;continue;}
        if(!ids[i])ids[i]=Icall<int(*)(Il2CppString*)>("UnityEngine.Shader::PropertyToID")(il2cpp_string_new(names[i]));
        Icall<void(*)(void*,int,void*)>("UnityEngine.Material::GetColorImpl_Injected")(material,ids[i],snapshot.colors+4*i);
        for(unsigned j=0;j<4;++j)if(!std::isfinite(snapshot.colors[4*i+j]))Fail("nonfinite outline palette");
    }
    {std::lock_guard<std::mutex> guard(state->paletteLock);state->palette=snapshot;}
}
static void AfterOutlineEnable() {
    if(!activeState||activeState->retired.load())return;
    auto* outline=Class("Assembly-CSharp.dll","","OutlineLayer");
    auto* field=il2cpp_class_get_field_from_name(outline,"outlineColorCmd");
    if(!field||!(il2cpp_field_get_flags(field)&0x10))Fail("outline command field ABI");
    Il2CppObject* commands=nullptr;il2cpp_field_static_get_value(field,&commands);if(!commands)return;
    Icall<void(*)(void*,void*,int,void*)>("UnityEngine.Rendering.CommandBuffer::IssuePluginEventAndDataInternal")
        (commands,reinterpret_cast<void*>(&PaletteDraw),0,activeState);
    DiscoSceneResidency::Log("Outline palette callback appended after original color blit\n");
}
// Queue the binding next to the GPU copy, so camera globals cannot replace it
// between main-thread setup and OutlineLayer's later color command.
static void QueueBinding(State* state,Il2CppObject* texture) {
    auto* klass=Class("UnityEngine.CoreModule.dll","UnityEngine.Rendering","RenderTargetIdentifier");
    uint32_t alignment=0;if(il2cpp_class_value_size(klass,&alignment)!=40)Fail("render target identifier ABI");
    const MethodInfo* ctor=nullptr;void* cursor=nullptr;
    while(auto* method=il2cpp_class_get_methods(klass,&cursor)){
        if(std::strcmp(method->name,".ctor")||il2cpp_method_get_param_count(method)!=1)continue;
        auto* parameter=il2cpp_class_from_type(il2cpp_method_get_param(method,0));
        if(parameter&&!std::strcmp(il2cpp_class_get_name(parameter),"Texture")&&
           !std::strcmp(il2cpp_class_get_namespace(parameter),"UnityEngine"))ctor=method;
    }
    if(!ctor)Fail("render target texture constructor ABI");
    alignas(8) uint8_t identifier[40]{};
    // Value-type metadata can expose a boxed adjustor. This pinned original
    // body takes the unboxed, checked 40-byte identifier directly.
    reinterpret_cast<void(*)(void*,void*,const MethodInfo*)>(module->image->At(0xfd4054,4,4))(identifier,texture,ctor);
    Icall<void(*)(void*,int,const void*,int)>("UnityEngine.Rendering.CommandBuffer::SetGlobalTexture_Impl")
        (Object(state->commands),state->property,identifier,0);
}
static void Pump() {
    for(auto* state:states){
        if(!state->retired.load()&&state->camera&&!Alive(Object(state->camera)))Retire(state);
        if(state->retired.load()||!state->hasProperty||!state->ready.load(std::memory_order_acquire))continue;
        if(state->bound){UpdatePalette(state);continue;}
        auto* klass=Class("UnityEngine.CoreModule.dll","UnityEngine","RenderTexture");
        auto* texture=il2cpp_object_new(klass);state->external=il2cpp_gchandle_new(texture,false);
        int depth=0;void* dimensions[]={&state->width,&state->height,&depth};Call(klass,".ctor",3,texture,dimensions);
        Icall<void(*)(void*,int)>("UnityEngine.RenderTexture::set_graphicsFormat")(texture,13);
        if(!Boolean(Call(klass,"Create",0,texture,nullptr)))Fail("integer stencil render texture creation");
        uintptr_t native=uintptr_t(Icall<void*(*)(void*)>("UnityEngine.Texture::GetNativeTexturePtr")(texture));
        if(!native||native>UINT32_MAX)Fail("integer stencil native ownership");
        state->resolvedTexture.store(GLuint(native),std::memory_order_release);
        Icall<void(*)(void*,int)>("UnityEngine.Texture::set_filterMode")(texture,0);
        Icall<void(*)(int,void*,int)>("UnityEngine.Shader::SetGlobalRenderTextureImpl")(state->property,texture,0);
        QueueBinding(state,texture);
        state->bound=true;DiscoSceneResidency::Log("GLES stencil texture bound to original outline shader\n");
    }
}
}
