// Original offscreen GLES compile/link diagnostic. Extracted shaders stay local.
#include <EGL/egl.h>
#include <GLES3/gl3.h>
#include <android/asset_manager.h>
#include <string>
#include <sstream>
#include <cstdlib>

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
    unsigned compiled = 0, linked = 0;
    std::ostringstream failures;
    bool anyFailure = false;
    for (long i = 0; i < count; ++i) {
        GLuint shaders[2] = {}; bool good = true; std::string error;
        for (unsigned stage = 0; stage < 2; ++stage) {
            char path[64]; snprintf(path,sizeof(path),"shader-%03ld.%s",i,stage ? "frag" : "vert");
            std::string text = Asset(assets,path);
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
        if (good && success) ++linked;
        else {
            if (anyFailure) failures << ',';
            if (good) { char message[2048] = {}; glGetProgramInfoLog(program,sizeof(message),nullptr,message); error += message; }
            failures << "{\"index\":" << i << ",\"log\":" << JsonText(error) << '}'; anyFailure = true;
        }
        glDeleteProgram(program); glDeleteShader(shaders[0]); glDeleteShader(shaders[1]);
    }
    std::string decode = DiscoBCDecodeReport();
    eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);
    eglDestroySurface(display,surface); eglDestroyContext(display,context); eglTerminate(display);
    std::ostringstream result;
    result << "{\"included\":" << (count ? "true" : "false") << ",\"pairs\":" << count << ",\"stages_compiled\":" << compiled
           << ",\"pairs_linked\":" << linked << ",\"gl_version\":" << JsonText(glVersion) << ",\"failures\":[" << failures.str()
           << "],\"bc_decode_trial\":" << decode << ",\"scope\":\"Compile/link only; no material binding or render-fidelity validation\"}";
    return result.str();
}
