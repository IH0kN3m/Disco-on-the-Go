#!/usr/bin/env python3
"""Check every staged GLES shader variant; source and diagnostics stay private."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import subprocess
import UnityPy
from UnityPy.helpers import CompressionHelper as C
from disco_port.android_shader_audit import program_sources,stage_source,referenced_programs
from disco_port.binary import FormatError

ROOT=Path(__file__).resolve().parent.parent


def inputs(root):
    for path in sorted(root.rglob('*')):
        if path.is_symlink():raise FormatError('Asset symlinks are unsupported')
        if not path.is_file():continue
        if path.suffix=='.assets' or path.name in ('unity_builtin_extra','globalgamemanagers') or re.fullmatch(r'level\d+',path.name):
            yield path;continue
        with path.open('rb') as stream:signature=stream.read(8)
        if signature==b'UnityFS\0':yield path


def main(validator):
    if UnityPy.__version__!='1.25.4':raise FormatError('Expected UnityPy 1.25.4')
    version=subprocess.check_output([str(validator),'--version'],text=True)
    if 'Glslang Version: 11:16.6.0' not in version:raise FormatError('Expected pinned glslang 16.6.0')
    base=ROOT/'artifacts/android/game-data';output=ROOT/'artifacts/android/shader-audit';output.mkdir(parents=True,exist_ok=True)
    sources={};records=[];errors=[];files=0;types=Counter();refs=0;extensions=Counter()
    for root in (base/'apk/bin/Data',base/'external/GameFiles/StreamingAssets'):
        if not root.is_dir():raise FormatError('Stage Android assets before auditing')
        for path in inputs(root):
            files+=1
            try:
                env=UnityPy.load(str(path))
                for obj in env.objects:
                    if obj.type.name!='Shader':continue
                    d=obj.read_typetree();name=d['m_ParsedForm']['m_Name']
                    if d['platforms']!=[9]:raise FormatError('Non-Android shader platform')
                    offsets,lengths,sizes=[d[key][0] for key in ('offsets','compressedLengths','decompressedLengths')]
                    if not 0<len(offsets)<=64 or not len(offsets)==len(lengths)==len(sizes):raise FormatError('Shader segment table mismatch')
                    blob=bytes(d['compressedBlob']);segments=[];ranges=[]
                    for offset,length,size in zip(offsets,lengths,sizes):
                        if offset<0 or not 0<length<=len(blob)-offset or not 4<=size<=256*1024**2:raise FormatError('Shader segment bounds invalid')
                        if any(offset<end and begin<offset+length for begin,end in ranges):raise FormatError('Overlapping compressed shader segments')
                        ranges.append((offset,offset+length));raw=C.decompress_lz4(blob[offset:offset+length],size)
                        if len(raw)!=size:raise FormatError('Shader expanded size mismatch')
                        segments.append(raw)
                    programs=program_sources(segments);references=referenced_programs(d['m_ParsedForm'],len(programs));refs+=len(references)
                    for index,kind,_ in references:
                        if programs[index]['type']!=kind:raise FormatError('Shader variant type differs from program table')
                    hashes=[]
                    for program in programs:
                        types[program['type']]+=1;source=program['source'];digest=hashlib.sha256(source.encode()).hexdigest();hashes.append(digest)
                        if digest not in sources:
                            for ext in set(re.findall(r'^\s*#extension\s+(\w+)',source,re.M)):extensions[ext]+=1
                            sources[digest]={'vertex':stage_source(source,'vertex',program['type']),'fragment':stage_source(source,'fragment',program['type'])}
                    records.append({'file':str(path.relative_to(base)),'id':obj.path_id,'name':name,'programs':hashes,'variant_references':len(references)})
            except (ValueError,KeyError,IndexError,TypeError) as e:
                errors.append({'file':str(path.relative_to(base)),'error':str(e)})
    def compile_pair(item):
        digest,stages=item;paths=[]
        for stage,suffix in (('vertex','vert'),('fragment','frag')):
            p=output/(digest+'.'+suffix);p.write_text(stages[stage]);paths.append(p)
        result=subprocess.run([str(validator),'-l',*map(str,paths)],capture_output=True,text=True,timeout=30)
        (output/(digest+'.log')).write_text(result.stdout+result.stderr)
        return {'sha256':digest,'linked':result.returncode==0}
    with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(compile_pair,sources.items()))
    failures=[r for r in results if not r['linked']]
    report={'scope':'Every staged shader source compiled/linked by the pinned reference compiler; GPU execution and scene fidelity require device testing',
            'serialized_containers_checked':files,'shaders':len(records),'programs':sum(types.values()),'variant_references':refs,
            'program_types':dict(types),'unique_pairs':len(results),'linked_pairs':len(results)-len(failures),'extensions':dict(extensions),
            'structural_errors':errors,'compiler_failures':failures,'inventory':records,'validator_version':version}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('inventory','validator_version','compiler_failures','structural_errors')},indent=2))
    if errors or failures:raise FormatError(f'{len(errors)} structural errors and {len(failures)} compile/link failures; inspect private shader-audit/report.json')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validator',type=Path,default=ROOT/'artifacts/toolchains/glslang-16.6.0/bin/glslang')
    args=parser.parse_args();main(args.validator.resolve())
