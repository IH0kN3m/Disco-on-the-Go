// Original full-screen, lossless unsigned stencil transfer. Shared with the GPU regression probe.
#pragma once
namespace DiscoStencilPrograms {
static const char* const codes[]={"#version 300 es\nvoid main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.-1.,0.,1.);}",
            "#version 300 es\nprecision highp float;precision highp usampler2D;uniform usampler2D s;layout(location=0) out highp uvec4 c;void main(){c=texelFetch(s,ivec2(gl_FragCoord.xy),0);}"};
static const char* const paletteFragment="#version 300 es\nprecision highp float;precision highp usampler2D;uniform usampler2D s;uniform vec4 palette[16];uniform ivec2 targetSize;layout(location=0) out vec4 c;void main(){ivec2 p=ivec2(gl_FragCoord.xy*vec2(textureSize(s,0))/vec2(targetSize));c=palette[int(texelFetch(s,p,0).r&15u)];}";
}
