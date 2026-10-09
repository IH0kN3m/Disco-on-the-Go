"""Bounded PE/CLI inspection; never load a supplied Windows executable."""
import struct
from .binary import FormatError


def pe_info(data):
    def read(fmt, offset):
        if offset<0 or offset+struct.calcsize(fmt)>len(data):raise FormatError('PE read outside file')
        return struct.unpack_from(fmt,data,offset)
    if len(data)<64 or data[:2]!=b'MZ':raise FormatError('Expected PE DOS header')
    pe=read('<I',60)[0]
    if data[pe:pe+4]!=b'PE\0\0':raise FormatError('Invalid PE signature')
    machine,count,_,_,_,optional_size,_=read('<HHIIIHH',pe+4)
    optional=pe+24; magic=read('<H',optional)[0]
    if machine not in (0x14c,0x8664,0xaa64) or magic not in (0x10b,0x20b) or not 0<count<=96:
        raise FormatError('Unsupported PE architecture/header')
    directory_offset=96 if magic==0x10b else 112
    if optional_size<directory_offset or optional+optional_size+40*count>len(data):raise FormatError('Truncated PE optional header/sections')
    directories=read('<I',optional+directory_offset-4)[0]
    if directories>16 or directory_offset+8*directories>optional_size:raise FormatError('Invalid PE directory count')
    sections=[]
    for n in range(count):
        at=optional+optional_size+40*n
        virtual_size,va,raw_size,raw=read('<4I',at+8)
        if raw_size and raw+raw_size>len(data):raise FormatError('PE section escapes file')
        sections.append((va,virtual_size,raw,raw_size))
    def offset(rva,size):
        owners=[raw+rva-va for va,vs,raw,rs in sections if va<=rva and rva+size<=va+rs and rva+size<=va+max(vs,rs)]
        if not 0<size<=128*1024**2 or len(owners)!=1:raise FormatError('PE RVA has missing or ambiguous section ownership')
        return owners[0]
    result={'machine':{0x14c:'x86',0x8664:'x64',0xaa64:'arm64'}[machine], 'cli':False}
    if directories<=14:return result
    cli_rva,cli_size=read('<II',optional+directory_offset+14*8)
    if cli_rva==cli_size==0:return result
    if cli_size<72:raise FormatError('Truncated CLI header')
    cli=offset(cli_rva,72)
    metadata_rva,metadata_size=read('<II',cli+8)
    metadata=offset(metadata_rva,metadata_size);end=metadata+metadata_size
    if data[metadata:metadata+4]!=b'BSJB':raise FormatError('Invalid CLI metadata signature')
    version_size=read('<I',metadata+12)[0]
    if not 0<version_size<=256 or metadata+16+version_size>end:raise FormatError('Invalid CLI version length')
    cursor=(metadata+16+version_size+3)&~3
    if cursor+4>end:raise FormatError('Truncated CLI stream header')
    _,streams=read('<HH',cursor);cursor+=4
    if not 0<streams<=16:raise FormatError('Invalid CLI stream count')
    found={}
    for _ in range(streams):
        if cursor+8>end:raise FormatError('Truncated CLI stream descriptor')
        relative,size=read('<II',cursor);cursor+=8
        stop=data.find(b'\0',cursor,min(cursor+32,end))
        if stop<0:raise FormatError('Unterminated CLI stream name')
        try:name=data[cursor:stop].decode('ascii')
        except UnicodeDecodeError:raise FormatError('Invalid CLI stream name') from None
        cursor=(stop+4)&~3
        if not name or name in found or relative+size>metadata_size:raise FormatError('Invalid/duplicate CLI stream bounds')
        found[name]=(metadata+relative,size)
    ranges=sorted((start,start+size) for start,size in found.values() if size)
    if any(start<cursor for start,_ in ranges) or any(a[1]>b[0] for a,b in zip(ranges,ranges[1:])):
        raise FormatError('CLI streams overlap headers or each other')
    tables=[found[n] for n in ('#~','#-') if n in found]
    if len(tables)!=1:raise FormatError('Expected one CLI table stream')
    table,size=tables[0];table_end=table+size
    if size<24:raise FormatError('Truncated CLI tables')
    heap_sizes=data[table+6];valid=read('<Q',table+8)[0]
    rows={};at=table+24
    for n in range(64):
        if valid>>n&1:
            if at+4>table_end:raise FormatError('Truncated CLI row counts')
            rows[n]=read('<I',at)[0];at+=4
            if rows[n]>1000000:raise FormatError('CLI table count exceeds scope')
    index=lambda n:4 if rows.get(n,0)>=65536 else 2
    coded=lambda ns,bits:4 if max(rows.get(n,0) for n in ns)>=(1<<(16-bits)) else 2
    string=4 if heap_sizes&1 else 2;guid=4 if heap_sizes&2 else 2;blob=4 if heap_sizes&4 else 2
    strides=[2+string+3*guid,coded((0,26,35,1),2)+2*string,
             4+2*string+coded((2,1,27),2)+index(4)+index(6),index(4),2+string+blob,index(6)]
    for n,stride in enumerate(strides):at+=rows.get(n,0)*stride
    methods=rows.get(6,0);stride=8+string+blob+index(8)
    if at+methods*stride>table_end:raise FormatError('Method definitions exceed CLI stream')
    bodies=stub_like=0
    for n in range(methods):
        rva=read('<I',at+n*stride)[0]
        if not rva:continue
        body=offset(rva,1);first=data[body]
        if first&3==2:header=1;length=first>>2
        elif first&3==3:
            header=(read('<H',body)[0]>>12)*4
            if header<12:raise FormatError('Invalid fat IL header')
            offset(rva,header);length=read('<I',body+4)[0]
        else:raise FormatError('Unsupported non-IL method body')
        offset(rva,header+length)
        code=data[body+header:body+header+length];bodies+=1
        if code in (b'\x2a',b'\x14\x7a',b'\x14\x2a',b'\x16\x2a'):stub_like+=1
    result.update(cli=True,method_definitions=methods,il_bodies=bodies,trivial_or_stub_like_bodies=stub_like,
                  note='Body presence is not proof of authentic game logic; metadata-only and placeholder assemblies need separate review.')
    return result
