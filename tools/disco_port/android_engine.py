"""Version-pinned host adaptation for desktop metadata in the Android player."""
import hashlib
import struct
from .binary import FormatError

UNITY_SHA256 = 'cf72dadd638cb87220e3d353776065629239edcb68416a5213b82149921515e3'


def executable_offset(data, address, size):
    if len(data)<64 or data[:7]!=b'\x7fELF\x02\x01\x01' or struct.unpack_from('<H',data,18)[0]!=183:
        raise FormatError('Expected little-endian ARM64 ELF')
    table=struct.unpack_from('<Q',data,32)[0]
    entry,count=struct.unpack_from('<HH',data,54)
    if entry!=56 or not 0<count<=128 or table+entry*count>len(data):raise FormatError('Invalid ELF program headers')
    matches=[]
    for i in range(count):
        kind,flags,offset,va,_,file_size,memory_size,_=struct.unpack_from('<IIQQQQQQ',data,table+i*entry)
        if kind!=1:continue
        if file_size>memory_size or offset+file_size>len(data):raise FormatError('Invalid ELF segment ownership')
        if flags&1 and va<=address and size>0 and address+size<=va+file_size:matches.append(offset+address-va)
    if len(matches)!=1:raise FormatError('Patch has no unique executable owner')
    return matches[0]


def adapt_desktop_audio(data):
    if hashlib.sha256(data).hexdigest()!=UNITY_SHA256:raise FormatError('Unsupported Unity Android player fingerprint')
    # This complete, three-instruction function only forwards a mobile-only
    # managed event. Actual native audio focus, volume and playback remain intact.
    offset=executable_offset(data,0x1041278,12)
    if struct.unpack_from('<III',data,offset)!=(0x12000020,0xaa1f03e1,0x17c9131b):raise FormatError('Unexpected mute-notification function')
    output=bytearray(data);struct.pack_into('<I',output,offset,0xd65f03c0)
    return bytes(output)
