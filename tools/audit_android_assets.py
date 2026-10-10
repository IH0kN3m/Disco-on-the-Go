#!/usr/bin/env python3
"""Verify preserved game objects and texture/shader ownership across staged assets."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import UnityPy
from disco_port.build_inputs import validate_sources
from disco_port.binary import FormatError
from disco_port.android_asset_audit import validate_texture_shape

ROOT=Path(__file__).resolve().parent.parent
ALLOWED_CHANGES={'Shader','BuildSettings','PlayerSettings','ScriptMapper','GraphicsSettings'}


def owned_objects(env,platform):
    result={};externals={}
    for asset in env.assets:
        if asset.header.version!=22 or asset.unity_version!='2020.3.12f1' or asset._m_target_platform!=platform:
            raise FormatError('Unsupported serialized version/platform')
        key=asset.name
        if key in externals:raise FormatError('Duplicate serialized child name')
        externals[key]=asset.externals
        for obj in asset.objects.values():
            result[key,obj.path_id]=obj
    if not externals:raise FormatError('No serialized children')
    return result,externals


def main():
    if UnityPy.__version__!='1.25.4':raise FormatError('Expected UnityPy 1.25.4')
    validate_sources(ROOT/'reference/Disco.app')
    source=ROOT/'reference/Disco.app/Contents/Resources/Data';base=ROOT/'artifacts/android/game-data'
    manifest=json.loads((base/'manifest.json').read_text());errors=[];preserved=Counter();changed=Counter();texture_formats=Counter();shader_refs=Counter();containers=0;copied=0
    for record in manifest['files']:
        before=source/record['source'];after=base/record['target']
        # Earlier private iterations moved Amplify to the mapped data path.
        # Audit that final location too; current staging writes it directly.
        if record['source'].startswith('AmplifyTexture/'):
            after=base/'external/GameFiles/Resources/Data'/record['source']
        for path,root in ((before,source),(after,base)):
            if not path.resolve().is_relative_to(root.resolve()) or path.is_symlink() or not path.is_file():raise FormatError('Asset path escapes its source/target ownership')
        with before.open('rb') as stream:signature=stream.read(8)
        relative=record['source'];serialized=bool(re.fullmatch(r'(globalgamemanagers(?:\.assets)?|level\d+|sharedassets\d+\.assets|resources\.assets)',relative)) or relative=='Resources/unity_builtin_extra'
        try:
            if not serialized and signature!=b'UnityFS\0':
                if relative=='boot.config':before=ROOT/'artifacts/android/unity-export/unityLibrary/src/main/assets/bin/Data/boot.config'
                with before.open('rb') as a,after.open('rb') as b:
                    if hashlib.file_digest(a,'sha256').digest()!=hashlib.file_digest(b,'sha256').digest():raise FormatError('Unconverted source bytes changed')
                copied+=1;continue
            containers+=1
            original,_=owned_objects(UnityPy.load(str(before)),2)
            derived,externals=owned_objects(UnityPy.load(str(after)),13)
            if not set(original)<=set(derived):raise FormatError('Original object IDs were removed')
            for key,obj in original.items():
                target=derived[key]
                if obj.type!=target.type:raise FormatError('Original object type changed')
                same=obj.get_raw_data()==target.get_raw_data()
                if not same and obj.type.name not in ALLOWED_CHANGES:raise FormatError('Unreviewed object bytes changed: '+obj.type.name)
                (preserved if same else changed)[obj.type.name]+=1
            for key,target in derived.items():
                if key not in original and (relative!='Resources/unity_builtin_extra' or target.type.name!='Shader'):
                    raise FormatError('Unexpected added object')
                if target.type.name=='Material':
                    pointer=target.read_typetree()['m_Shader'];file_id=pointer['m_FileID'];path_id=pointer['m_PathID']
                    if not path_id:continue
                    if not 0<=file_id<=len(externals[key[0]]):raise FormatError('Material shader file ID escapes ownership')
                    owner=key[0] if not file_id else externals[key[0]][file_id-1].path
                    shader_refs[(Path(owner).name,path_id)]+=1
                    if not file_id and (key[0],path_id) not in derived:raise FormatError('Missing local material shader')
                    if not file_id and derived[key[0],path_id].type.name!='Shader':raise FormatError('Material references a non-shader object')
                elif target.type.name=='Texture2D':
                    texture=target.read_typetree();validate_texture_shape(texture)
                    texture_formats[texture['m_TextureFormat']]+=1
        except (ValueError,KeyError,TypeError,IndexError) as e:errors.append({'source':relative,'error':str(e)})
    output=ROOT/'artifacts/android/asset-audit.json'
    report={'scope':'All supplied staged asset files compared; original non-adapted object bytes preserved. External shader references are inventoried, not complete scene execution.',
            'containers_checked':containers,'copied_files_checked':copied,'preserved_objects':dict(preserved),'adapted_objects':dict(changed),'texture_formats':dict(texture_formats),
            'material_shader_references':[{'file':file,'id':path,'references':count} for (file,path),count in sorted(shader_refs.items())], 'errors':errors}
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('material_shader_references','errors')},indent=2))
    if errors:raise FormatError(f'{len(errors)} asset integrity errors; inspect private asset-audit.json')


if __name__=='__main__':main()
