"""Bounded reader for linked ARM64 compact unwind tables; never executes code."""
import struct
from .binary import FormatError


def records(data):
    def read(fmt, offset):
        size=struct.calcsize(fmt)
        if offset<0 or offset+size>len(data):raise FormatError('Unwind table read outside section')
        return struct.unpack_from(fmt,data,offset)
    version,co,cn,po,pn,io,count=read('<7I',0)
    if version!=1 or cn>256 or pn>3 or not 2<=count<=65536:
        raise FormatError('Unsupported unwind header')
    common=read(f'<{cn}I',co);personalities=read(f'<{pn}I',po)
    indices=[read('<3I',io+12*i) for i in range(count)]
    if indices[-1][1] or any(a[0]>=b[0] for a,b in zip(indices,indices[1:])):
        raise FormatError('Unordered unwind pages or missing sentinel')
    output=[]
    for i,(first,page,lsda) in enumerate(indices[:-1]):
        limit,_,lsda_end=indices[i+1]
        if not page or lsda_end<lsda or (lsda_end-lsda)%8:
            raise FormatError('Invalid unwind page/LSDA range')
        entries={}
        for at in range(lsda,lsda_end,8):
            function,address=read('<2I',at)
            if function in entries or not first<=function<limit:raise FormatError('Invalid LSDA owner')
            entries[function]=address
        kind,eo,n=read('<IHH',page)
        if not 0<n<=1021:raise FormatError('Invalid unwind page entry count')
        if kind==3:
            extra,extra_count=read('<HH',page+8)
            if cn+extra_count>256:raise FormatError('Unwind encoding index overflow')
            encodings=common+read(f'<{extra_count}I',page+extra)
        elif kind!=2:raise FormatError('Unknown unwind page kind')
        for j in range(n):
            if kind==2:address,encoding=read('<2I',page+eo+j*8)
            else:
                value,=read('<I',page+eo+j*4);index=value>>24
                if index>=len(encodings):raise FormatError('Unowned unwind encoding')
                address=first+(value&0xffffff);encoding=encodings[index]
            if not first<=address<limit or (output and address<=output[-1]['start']):
                raise FormatError('Unordered or unowned unwind function')
            personality=(encoding>>28)&3
            if personality>pn:raise FormatError('Unowned unwind personality')
            has_lsda=bool(encoding&0x40000000)
            if has_lsda!=(address in entries):raise FormatError('LSDA flag and ownership disagree')
            output.append({'start':address,'encoding':encoding,'lsda':entries.get(address,0),
                           'personality_slot':personalities[personality-1] if personality else 0})
    for i,record in enumerate(output):record['end']=output[i+1]['start'] if i+1<len(output) else indices[-1][0]
    return output
