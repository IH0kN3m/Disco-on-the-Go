"""Bounded v27 IL2CPP string-literal usage resolution for static inspection."""
from .binary import FormatError, unpack


class NativeLiterals:
    def __init__(self, metadata):
        magic, version = unpack(metadata, '<II', 0)
        if magic != 0xfab11baf or version != 27:
            raise FormatError('String usage resolution requires IL2CPP metadata v27')
        records, record_size, heap, heap_size = unpack(metadata, '<4I', 8)
        if (records < 256 or record_size % 8 or not 0 < record_size <= 8 * 1_000_000
                or heap < records + record_size or heap_size > 64 * 1024**2
                or heap + heap_size > len(metadata)):
            raise FormatError('Invalid literal table ownership')
        self.metadata = metadata
        self.records, self.count = records, record_size // 8
        self.heap, self.heap_size = heap, heap_size

    def resolve(self, encoded):
        # MetadataUsage StringLiteral = 5, low bit marks an encoded unresolved
        # usage; initialized runtime pointers are never accepted as indexes.
        if type(encoded) is not int or not 0 <= encoded < 2**32 or encoded >> 29 != 5 or not encoded & 1:
            raise FormatError('Not an unresolved v27 string-literal usage')
        index = (encoded & 0x1fffffff) >> 1
        if index >= self.count:
            raise FormatError('Literal index outside owned records')
        length, offset = unpack(self.metadata, '<II', self.records + index * 8)
        if length > 1024**2 or offset + length > self.heap_size:
            raise FormatError('Literal bytes escape owned heap')
        try:
            return self.metadata[self.heap + offset:self.heap + offset + length].decode('utf-8')
        except UnicodeDecodeError as error:
            raise FormatError('Invalid literal UTF-8') from error
