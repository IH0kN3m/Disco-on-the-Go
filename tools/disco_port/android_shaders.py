"""Strict, limited GLCore-to-GLES compile experiment; not a Unity shader rebuilder."""
import re
from .binary import FormatError


def gles_stage(source, stage):
    if stage not in ('vertex','fragment') or not isinstance(source,str) or len(source)>1024*1024 or '\0' in source:
        raise FormatError('Unsupported shader source/stage')
    versions=re.findall(r'^\s*#version\s+(\d+)\s*$',source,re.M)
    if not versions or any(v not in ('330','410','420','430') for v in versions):
        raise FormatError('Unsupported desktop GLSL version')
    if '#ifdef VERTEX' not in source or '#ifdef FRAGMENT' not in source:
        raise FormatError('Expected paired Unity desktop vertex/fragment source')
    text=re.sub(r'^\s*#version\s+\d+\s*$','',source,flags=re.M)
    text=re.sub(r'^\s*#extension GL_ARB_explicit_attrib_location : require\s*$','',text,flags=re.M)
    # GLES 3.1+ retains the explicit locations used by Unity sampler bindings.
    # GLES 3.2 supplies the precision/420pack features used by these samples.
    text=re.sub(r'^\s*#extension GL_ARB_shading_language_420pack : require\s*$','',text,flags=re.M)
    extensions=re.findall(r'^\s*(#extension[^\n]+)',text,re.M)
    text=re.sub(r'^\s*#extension[^\n]+','',text,flags=re.M)
    precision='\n'.join('precision highp '+t+';' for t in ('float','int','sampler2D','sampler3D','samplerCube','sampler2DArray','sampler2DShadow','samplerCubeShadow','sampler2DArrayShadow','usampler2D','isampler2D','sampler2DMS','isampler2DMS','usampler2DMS'))
    return '#version 320 es\n#define '+stage.upper()+' 1\n'+'\n'.join(dict.fromkeys(extensions))+'\n'+precision+'\n'+text
