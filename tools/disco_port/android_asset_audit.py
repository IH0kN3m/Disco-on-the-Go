"""Validation of serialized texture shapes, including empty dynamic font atlases."""
from .binary import FormatError


def validate_texture_shape(texture):
    width,height=texture['m_Width'],texture['m_Height'];mips=texture['m_MipCount'];stream=texture['m_StreamData']
    if any(type(v) is not int for v in (width,height,mips,stream['offset'],stream['size'])):
        raise FormatError('Non-integer texture dimensions or stream range')
    if stream['offset']<0 or stream['size']<0 or stream['offset']+stream['size']>=2**64:
        raise FormatError('Invalid texture stream range')
    if stream['size'] and (not stream['path'] or texture['image data']):raise FormatError('Ambiguous texture data ownership')
    if width==height==0:
        if mips!=1 or texture['image data'] or stream['size'] or texture['m_CompleteImageSize']:
            raise FormatError('Nonempty zero-sized texture')
        return 'dynamic_empty'
    if not 1<=width<=32768 or not 1<=height<=32768 or not 1<=mips<=max(width,height).bit_length():
        raise FormatError('Unsupported texture dimensions/mips')
    return 'stored'
