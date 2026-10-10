#!/usr/bin/env python3
"""Rebuild private serialized shader variants for the GLES Android player."""
import json
from pathlib import Path
import UnityPy
from UnityPy.helpers import CompressionHelper as C
from disco_port.android_shader_blob import convert_segments
ROOT=Path(__file__).resolve().parent.parent


def convert_shader(obj):
    data=obj.read_typetree()
    if data['platforms']==[9]:return None
    if 15 not in data['platforms']:raise ValueError('Shader has no GLCore platform')
    i=data['platforms'].index(15)
    offsets,lengths,sizes=[data[key][i] for key in ('offsets','compressedLengths','decompressedLengths')]
    if not len(offsets)==len(lengths)==len(sizes):raise ValueError('Shader segment table mismatch')
    blob=bytes(data['compressedBlob']);segments=[]
    for offset,length,size in zip(offsets,lengths,sizes):
        if offset<0 or not 0<length<=len(blob)-offset or not 4<=size<=128*1024**2:raise ValueError('Shader blob bounds invalid')
        raw=C.decompress_lz4(blob[offset:offset+length],size)
        if len(raw)!=size:raise ValueError('Shader length mismatch')
        segments.append(raw)
    rebuilt=segments[0] if segments==[bytes(4)] else convert_segments(segments);compressed=C.compress_lz4(rebuilt)
    data.update(platforms=[9],offsets=[[0]],compressedLengths=[[len(compressed)]],decompressedLengths=[[len(rebuilt)]],compressedBlob=compressed)
    for subshader in data['m_ParsedForm']['m_SubShaders']:
        for shader_pass in subshader['m_Passes']:
            shader_pass['m_Platforms']=[9]
            for name,program in shader_pass.items():
                if not name.startswith('prog') or not isinstance(program,dict):continue
                selected=[s for s in program['m_SubPrograms'] if s['m_GpuProgramType'] in (6,7,8)]
                for sub in selected:sub['m_GpuProgramType']=3
                program['m_SubPrograms']=selected
    obj.save_typetree(data)
    return data['m_ParsedForm']['m_Name']


def main(bundles=False):
    root=ROOT/('artifacts/android/game-data/external/GameFiles/StreamingAssets' if bundles else 'artifacts/android/game-data/apk/bin/Data');report=[];errors=[]
    for path in sorted(root.rglob('*')):
        if not path.is_file():continue
        if bundles:
            with path.open('rb') as stream:signature=stream.read(8)
            if signature!=b'UnityFS\0':continue
        elif path.suffix!='.assets' and path.name!='unity_builtin_extra':continue
        env=UnityPy.load(path.read_bytes());changed=[]
        for obj in env.objects:
            if obj.type.name!='Shader':continue
            try:
                name=convert_shader(obj)
                if name:changed.append(name)
            except (ValueError,KeyError) as e:errors.append({'file':str(path.relative_to(root)),'id':obj.path_id,'error':str(e)})
        if changed:
            if len(env.files)!=1:raise ValueError('Expected single serialized asset')
            container=next(iter(env.files.values()));derived=container.save(packer='lz4') if bundles else container.save()
            temporary=path.with_name(path.name+'.shader-tmp');temporary.write_bytes(derived);temporary.replace(path);report.append({'file':str(path.relative_to(root)),'shaders':changed})
    out=ROOT/'artifacts/android/game-data'/('bundle-shaders.json' if bundles else 'shaders-latest.json');out.write_text(json.dumps({'converted':report,'unsupported':errors,'scope':'GLES source and Unity program mapping adapted; visual parity unverified'},indent=2)+'\n')
    print('Converted',sum(len(r['shaders']) for r in report),'shaders; unsupported:',len(errors))

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--bundles',action='store_true');args=parser.parse_args();main(args.bundles)
