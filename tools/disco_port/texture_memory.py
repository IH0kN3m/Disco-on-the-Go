"""Exact mip byte counts; estimates exclude allocators, CPU copies and working buffers."""

from .binary import FormatError

BC_FORMATS = {'DXT1': (8, 4), 'DXT1Crunched': (8, 4), 'DXT5': (16, 4),
              'DXT5Crunched': (16, 4), 'BC7': (16, 4), 'BC6H': (16, 8)}


def mip_sizes(width, height, mip_count, block_bytes, pixel_bytes):
    if any(type(x) is not int for x in (width, height, mip_count, block_bytes, pixel_bytes)):
        raise FormatError('Texture dimensions and byte sizes must be integers')
    if not 1 <= width <= 32768 or not 1 <= height <= 32768:
        raise FormatError('Unsupported texture dimensions')
    if not 1 <= mip_count <= max(width, height).bit_length():
        raise FormatError('Unsupported mip count')
    if block_bytes not in (8, 16) or pixel_bytes not in (4, 8):
        raise FormatError('Unsupported BC or fallback layout')
    compressed = fallback = 0
    levels = []
    for level in range(mip_count):
        compressed_level = ((width + 3) // 4) * ((height + 3) // 4) * block_bytes
        fallback_level = width * height * pixel_bytes
        levels.append({'level': level, 'width': width, 'height': height,
                       'bc_bytes': compressed_level, 'fallback_bytes': fallback_level})
        compressed += compressed_level
        fallback += fallback_level
        width, height = max(1, width // 2), max(1, height // 2)
    return {'bc_bytes': compressed, 'fallback_bytes': fallback, 'levels': levels}


def estimate_bc(format_name, width, height, mip_count):
    if format_name not in BC_FORMATS:
        return None
    return mip_sizes(width, height, mip_count, *BC_FORMATS[format_name])
