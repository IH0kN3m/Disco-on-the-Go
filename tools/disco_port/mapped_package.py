"""Private mapped-image packages from validated Mach-O plans."""
import struct
from .compact_unwind import records as unwind_records

def image_package(image,plan):
    names = sorted(set(b['symbol'] for b in plan['bindings']) | set(plan['exports']))
    strings = bytearray(); offsets = {}
    for name in names:
        offsets[name] = len(strings); strings += name.encode('ascii') + b'\0'
    pack = bytearray(struct.pack('<8s6IQ', b'DSCMAP01', len(image.segments), len(plan['rebases']),
                                len(plan['bindings']), len(plan['exports']), len(plan['initializers']), len(strings), len(image.data)))
    for s in image.segments:
        pack += struct.pack('<5Q', s.address, s.virtual_size, s.offset, s.file_size, s.protection)
    for r in plan['rebases']:
        pack += struct.pack('<2Q', r['address'], r['target'])
    for b in plan['bindings']:
        pack += struct.pack('<QIi qII', b['address'], offsets[b['symbol']], b['ordinal'], b['addend'],
                            b['flags'], {'bind': 0, 'lazy': 1, 'weak': 2}[b['kind']])
    for name, address in sorted(plan['exports'].items()):
        pack += struct.pack('<QII', address, offsets[name], 0)
    for address in plan['initializers']:
        pack += struct.pack('<Q', address)
    pack += strings; pack += image.data
    return bytes(pack)


def unwind_package(image):
    unwind_section = next(s for s in image.sections if s.name == '__unwind_info')
    eh_section = next(s for s in image.sections if s.name == '__eh_frame')
    unwind = unwind_records(image.data[unwind_section.offset:unwind_section.offset+unwind_section.size])
    uw = bytearray(struct.pack('<8sII', b'DSCUW001', len(unwind), eh_section.address))
    for index, record in enumerate(unwind):
        owner=next((s for s in image.sections if s.name in ('__text','il2cpp') and s.address<=record['start']<s.address+s.size),None)
        if owner and record['end']>owner.address+owner.size:
            if index!=len(unwind)-1:raise ValueError('Interior unwind interval crosses executable ownership')
            # The linker's final sentinel includes import stubs; those tail jumps
            # do not share the final generated method's frame description.
            record['end']=owner.address+owner.size
        if not image.executable(record['start']) or not image.executable(record['end']-1):
            raise ValueError('Unwind interval is not executable')
        for field in ('lsda','personality_slot'):
            if record[field]: image.offset_for_address(record[field], 8)
        uw += struct.pack('<5I', *(record[n] for n in ('start','end','encoding','lsda','personality_slot')))
    return bytes(uw)
