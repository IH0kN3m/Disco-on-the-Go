"""Validate the narrow Mach-O loader changes used by the iPad runtime."""

import hashlib
import re

from .binary import FormatError, MachO, read_string, unpack


LOAD_DYLIB = {0xC, 0x80000018, 0x8000001F, 0x20, 0x80000023}


def loader_info(data):
    image = MachO(data)
    if unpack(image.data, '<I', 12)[0] != 6:
        raise FormatError('iPad runtime requires a Mach-O dynamic library')
    count = unpack(image.data, '<I', 16)[0]
    cursor = 32
    dependencies, platforms = [], []
    for _ in range(count):
        command, length = unpack(image.data, '<II', cursor)
        if command in LOAD_DYLIB | {0xD}:
            if length < 24:
                raise FormatError('Truncated dynamic library command')
            start = unpack(image.data, '<I', cursor + 8)[0]
            if not 24 <= start < length:
                raise FormatError('Library name lies outside its owning command')
            name = read_string(image.data, cursor + start, cursor + length)
            if command in LOAD_DYLIB:
                dependencies.append(name)
        elif command == 0x32:
            if length < 24:
                raise FormatError('Truncated build version command')
            platform, minimum, sdk, tools = unpack(image.data, '<4I', cursor + 8)
            if length != 24 + tools * 8:
                raise FormatError('Unsupported build version tool layout')
            platforms.append(platform)
        cursor += length
    if len(platforms) != 1:
        raise FormatError('Expected one explicit Mach-O build platform')
    executable = {}
    for section in image.sections:
        if section.name in ('__text', 'il2cpp'):
            if section.name in executable:
                raise FormatError('Duplicate executable section name')
            # Verify both file bounds and ownership by its declared virtual address.
            if image.offset_for_address(section.address, section.size) != section.offset:
                raise FormatError('Executable section address/offset disagreement')
            executable[section.name] = hashlib.sha256(image.data[section.offset:section.offset + section.size]).hexdigest()
    if not executable:
        raise FormatError('Dynamic library contains no supported executable sections')
    return image, {'platform': platforms[0], 'dependencies': dependencies, 'executable_sha256': executable}


def ios_dependency(name):
    if name in {'/usr/lib/libSystem.B.dylib', '/usr/lib/libc++.1.dylib', '/usr/lib/libiconv.2.dylib', '/usr/lib/libobjc.A.dylib'}:
        return name
    match = re.fullmatch(r'/System/Library/Frameworks/(Foundation|Security|CoreFoundation)\.framework/Versions/[AC]/\1', name)
    if match:
        framework = match.group(1)
        return f'/System/Library/Frameworks/{framework}.framework/{framework}'
    raise FormatError(f'Unsupported runtime dependency: {name}')
