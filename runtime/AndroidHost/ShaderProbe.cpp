// Original offscreen GLES compile/link diagnostic. Extracted shaders stay local.
#include <EGL/egl.h>
#include <GLES3/gl3.h>
#include <GLES2/gl2ext.h>
#include <android/asset_manager.h>
#include <string>
#include <sstream>
#include <cstdlib>
#include <regex>
#include "StencilProbe.h"
#include "ReadbackProbe.h"

std::string DiscoBCDecodeReport();

static std::string Asset(AAssetManager* manager, const char* name) {
    AAsset* asset = AAssetManager_open(manager, name, AASSET_MODE_BUFFER);
    if (!asset) return {};
    off_t size = AAsset_getLength(asset);
    std::string text;
    if (size > 0 && size <= 1024 * 1024) {
        text.resize(size);
        if (AAsset_read(asset, &text[0], size) != size) text.clear();
    }
    AAsset_close(asset);
    return text;
}

static std::string JsonText(const std::string& text) {
    std::string result = "\"";
    for (char c : text) {
        if (c == '\\' || c == '\"') { result += '\\'; result += c; }
        else if (c == '\n') result += "\\n";
        else if (c >= 32 && c < 127) result += c;
    }
    return result + '\"';
}

std::string DiscoShaderReport(AAssetManager* assets) {
    std::string countText = Asset(assets, "shader-count.txt");
    char* end = nullptr;
    long count = countText.empty() ? 0 : strtol(countText.c_str(), &end, 10);
    if (!countText.empty() && (*end || count <= 0 || count > 64)) return "{\"error\":\"invalid sample count\"}";
    EGLDisplay display = eglGetDisplay(EGL_DEFAULT_DISPLAY);
    if (display == EGL_NO_DISPLAY || !eglInitialize(display, nullptr, nullptr)) return "{\"error\":\"EGL initialize\"}";
    EGLint attributes[] = {EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_ES3_BIT,
                          EGL_RED_SIZE,8,EGL_GREEN_SIZE,8,EGL_BLUE_SIZE,8,EGL_NONE};
    EGLConfig config; EGLint found = 0;
    eglBindAPI(EGL_OPENGL_ES_API);
    if (!eglChooseConfig(display, attributes, &config, 1, &found) || !found) {
        eglTerminate(display); return "{\"error\":\"EGL config\"}";
    }
    EGLint contextAttributes[] = {EGL_CONTEXT_CLIENT_VERSION,3,EGL_NONE};
    EGLint surfaceAttributes[] = {EGL_WIDTH,1,EGL_HEIGHT,1,EGL_NONE};
    EGLContext context = eglCreateContext(display, config, EGL_NO_CONTEXT, contextAttributes);
    EGLSurface surface = eglCreatePbufferSurface(display, config, surfaceAttributes);
    if (context == EGL_NO_CONTEXT || surface == EGL_NO_SURFACE || !eglMakeCurrent(display,surface,surface,context)) {
        if (context != EGL_NO_CONTEXT) eglDestroyContext(display,context);
        if (surface != EGL_NO_SURFACE) eglDestroySurface(display,surface);
        eglTerminate(display); return "{\"error\":\"EGL context\"}";
    }
    std::string glVersion = reinterpret_cast<const char*>(glGetString(GL_VERSION));
    std::ostringstream capabilities;
    capabilities << "{\"renderer\":" << JsonText(reinterpret_cast<const char*>(glGetString(GL_RENDERER))) << ",\"extensions\":[";
    GLint extensions=0;glGetIntegerv(GL_NUM_EXTENSIONS,&extensions);
    for(GLint i=0;i<extensions;++i){if(i)capabilities<<',';capabilities<<JsonText(reinterpret_cast<const char*>(glGetStringi(GL_EXTENSIONS,i)));}
    GLint textureSize=0,textureUnits=0;glGetIntegerv(GL_MAX_TEXTURE_SIZE,&textureSize);glGetIntegerv(GL_MAX_TEXTURE_IMAGE_UNITS,&textureUnits);
    capabilities << "],\"max_texture_size\":" << textureSize << ",\"fragment_texture_units\":" << textureUnits << ",\"render_targets\":[";
    GLuint target=0,framebuffer=0;glGenTextures(1,&target);glGenFramebuffers(1,&framebuffer);
    const GLenum formats[]={GL_R16_EXT,GL_RG16_EXT,GL_R32F,GL_RG32F,GL_RGBA8};
    const char* names[]={"R16_UNorm","RG16_UNorm","R32_SFloat","RG32_SFloat","RGBA8"};
    for(unsigned i=0;i<5;++i){
        while(glGetError()!=GL_NO_ERROR){}
        glBindTexture(GL_TEXTURE_2D,target);glTexStorage2D(GL_TEXTURE_2D,1,formats[i],2,2);
        GLenum error=glGetError();glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);
        glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,target,0);
        bool supported=error==GL_NO_ERROR&&glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE&&glGetError()==GL_NO_ERROR;
        if(i)capabilities<<',';capabilities<<"{\"name\":"<<JsonText(names[i])<<",\"renderable\":"<<(supported?"true":"false")<<'}';
        glDeleteTextures(1,&target);glGenTextures(1,&target);
    }
    glBindFramebuffer(GL_FRAMEBUFFER,0);glBindTexture(GL_TEXTURE_2D,0);glDeleteTextures(1,&target);glDeleteFramebuffers(1,&framebuffer);
    while(glGetError()!=GL_NO_ERROR){}
    capabilities << "]}";
    unsigned compiled = 0, linked = 0, samplerLocations = 0;
    std::ostringstream failures;
    bool anyFailure = false;
    for (long i = 0; i < count; ++i) {
        GLuint shaders[2] = {}; bool good = true; std::string error, sources;
        for (unsigned stage = 0; stage < 2; ++stage) {
            char path[64]; snprintf(path,sizeof(path),"shader-%03ld.%s",i,stage ? "frag" : "vert");
            std::string text = Asset(assets,path);
            sources += text;
            shaders[stage] = glCreateShader(stage ? GL_FRAGMENT_SHADER : GL_VERTEX_SHADER);
            const char* source = text.c_str(); GLint length = text.size();
            glShaderSource(shaders[stage],1,&source,&length); glCompileShader(shaders[stage]);
            GLint success = 0; glGetShaderiv(shaders[stage],GL_COMPILE_STATUS,&success);
            if (success) ++compiled; else {
                good = false; char message[2048] = {};
                glGetShaderInfoLog(shaders[stage], sizeof(message), nullptr, message);
                error += stage ? "fragment: " : "vertex: "; error += message;
            }
        }
        GLuint program = glCreateProgram();
        glAttachShader(program,shaders[0]); glAttachShader(program,shaders[1]); glLinkProgram(program);
        GLint success = 0; glGetProgramiv(program,GL_LINK_STATUS,&success);
        if (good && success) {
            const std::regex sampler(R"(UNITY_LOCATION\(([0-9]+)\)\s+uniform\s+(?:(?:highp|mediump|lowp)\s+)?[iu]?sampler\w+\s+(\w+))");
            for (auto it=std::sregex_iterator(sources.begin(),sources.end(),sampler);it!=std::sregex_iterator();++it) {
                GLint location=glGetUniformLocation(program,(*it)[2].str().c_str());
                if(location<0)continue; // Optimized out or excluded by the variant.
                if(location!=std::stoi((*it)[1].str())) { good=false; error+="explicit sampler location differs: "+(*it)[2].str(); }
                else ++samplerLocations;
            }
        }
        if (good && success) ++linked;
        else {
            if (anyFailure) failures << ',';
            if (good) { char message[2048] = {}; glGetProgramInfoLog(program,sizeof(message),nullptr,message); error += message; }
            failures << "{\"index\":" << i << ",\"log\":" << JsonText(error) << '}'; anyFailure = true;
        }
        glDeleteProgram(program); glDeleteShader(shaders[0]); glDeleteShader(shaders[1]);
    }
    std::string decode = DiscoBCDecodeReport();
    std::string stencil = StencilProbe();
    std::string integerStencil = StencilIntegerProbe();
    std::string readback = ReadbackProbe();
    eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);
    eglDestroySurface(display,surface); eglDestroyContext(display,context); eglTerminate(display);
    std::ostringstream result;
    result << "{\"included\":" << (count ? "true" : "false") << ",\"pairs\":" << count << ",\"stages_compiled\":" << compiled
           << ",\"pairs_linked\":" << linked << ",\"explicit_sampler_locations_checked\":" << samplerLocations << ",\"gl_version\":" << JsonText(glVersion) << ",\"failures\":[" << failures.str()
           << "],\"capabilities\":" << capabilities.str() << ",\"bc_decode_trial\":" << decode << ",\"stencil_trial\":" << stencil << ",\"integer_stencil_trial\":" << integerStencil << ",\"readback_trial\":" << readback << ",\"scope\":\"Compile/link and isolated GPU tests; game rendering unverified\"}";
    return result.str();
}
