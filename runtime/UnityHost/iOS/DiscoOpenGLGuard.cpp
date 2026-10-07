// Diagnostic boundary for a CPU-only derived Amplify plugin. These desktop
// imports are unavailable on iPadOS. Fail explicitly if the game enters that
// path; never fabricate successful readbacks or render black textures.
#include <cstdio>
#include <cstdlib>
#include <cstddef>
using GLenum = unsigned int;
using GLuint = unsigned int;
using GLint = int;
using GLsizei = int;
using GLboolean = unsigned char;
using GLsizeiptr = std::ptrdiff_t;
[[noreturn]] static void Unsupported(const char* function) {
    std::fprintf(stderr, "NATIVE AMPLIFY: unsupported desktop GPU call=%s\n", function);
    std::fflush(stderr);
    std::abort();
}
extern "C" {
void glBindBuffer(GLenum, GLuint) { Unsupported("glBindBuffer"); }
void glBindFramebuffer(GLenum, GLuint) { Unsupported("glBindFramebuffer"); }
void glBindTexture(GLenum, GLuint) { Unsupported("glBindTexture"); }
void glBufferData(GLenum, GLsizeiptr, const void*, GLenum) { Unsupported("glBufferData"); }
void glDeleteBuffers(GLsizei, const GLuint*) { Unsupported("glDeleteBuffers"); }
void glFramebufferTexture2D(GLenum, GLenum, GLenum, GLuint, GLint) { Unsupported("glFramebufferTexture2D"); }
void glGenBuffers(GLsizei, GLuint*) { Unsupported("glGenBuffers"); }
void glGenFramebuffers(GLsizei, GLuint*) { Unsupported("glGenFramebuffers"); }
void glGetTexImage(GLenum, GLint, GLenum, GLenum, void*) { Unsupported("glGetTexImage"); }
void* glMapBuffer(GLenum, GLenum) { Unsupported("glMapBuffer"); }
void glReadBuffer(GLenum) { Unsupported("glReadBuffer"); }
void glReadPixels(GLint, GLint, GLsizei, GLsizei, GLenum, GLenum, void*) { Unsupported("glReadPixels"); }
GLboolean glUnmapBuffer(GLenum) { Unsupported("glUnmapBuffer"); }
}
