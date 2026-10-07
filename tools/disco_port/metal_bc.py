"""Bounded embedded-bitcode ownership and function replacement validation."""
import re

from .binary import FormatError, MachO, unpack


def embedded_bitcode(data):
    image = MachO(data)
    if unpack(image.data, '<I', 12)[0] != 1:
        raise FormatError('Expected a Mach-O object, not an executable/library')
    sections = [s for s in image.sections if s.segment == '__LLVM' and s.name == '__bitcode']
    if len(sections) != 1:
        raise FormatError('Expected one owned embedded LLVM module')
    section = sections[0]
    end = section.offset + section.size
    command_end = 32 + unpack(image.data, '<I', 20)[0]
    if section.offset < command_end or not 0 < section.size < 1024**2 or end > len(image.data) or not any(
        s.offset <= section.offset and end <= s.offset + s.file_size for s in image.segments):
        raise FormatError('Embedded LLVM bounds or segment ownership invalid')
    return image.data[section.offset:end]


def rename_metal_definitions(text, functions):
    if '[151 x i32]' not in text or 'getelementptr inbounds %struct.GraphicsCaps, ptr %0, i64 0, i32 52' not in text:
        raise FormatError('Unsupported engine graphics capability structure')
    for name, symbol in functions.items():
        if len(re.findall(r'^define [^\n]*@' + re.escape(symbol) + r'\(', text, re.M)) != 1:
            raise FormatError('Missing or ambiguous pinned Metal definition')
        if '@DiscoOriginalMetal' + name + '(' in text:
            raise FormatError('Metal definition already replaced')
    for name, symbol in functions.items():
        text = text.replace('@' + symbol + '(', '@DiscoOriginalMetal' + name + '(')
    return text
