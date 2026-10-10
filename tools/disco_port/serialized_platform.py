"""A narrow loader-tag experiment; does not convert asset contents to iOS."""

import struct

from .binary import FormatError, read_string, unpack


def retag_serialized(data, target=9):
    if target not in (9, 13):
        raise FormatError("Only iOS and Android loader tags are supported")
    if len(data) < 48 or unpack(data, '>I', 8)[0] != 22:
        raise FormatError('Only serialized file header v22 is supported')
    if data[16:20] != bytes(4):
        raise FormatError('Only little-endian metadata with zero header padding is supported')
    metadata_size, file_size, data_offset, reserved = unpack(data, '>IQQQ', 20)
    metadata_end = 48 + metadata_size
    if file_size != len(data) or not 48 < metadata_end <= data_offset <= file_size or reserved != 0:
        raise FormatError('Invalid serialized metadata/file/data ownership')
    version = read_string(data, 48, min(metadata_end, 112))
    if version != '2020.3.12f1':
        raise FormatError('Expected Unity 2020.3.12f1 serialized data')
    offset = 48 + len(version.encode('utf-8')) + 1
    if offset + 5 > metadata_end:
        raise FormatError('Platform and type-tree fields exceed metadata')
    if unpack(data, '<i', offset)[0] != 2 or data[offset + 4] not in (0, 1):
        raise FormatError('Expected macOS platform and supported type-tree flag')
    derived = bytearray(data)
    struct.pack_into('<i', derived, offset, target)
    return bytes(derived), offset
