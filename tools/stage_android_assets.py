#!/usr/bin/env python3
"""Stage private Android game assets from the immutable Mac reference."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import copy
import UnityPy
from UnityPy.enums import BuildTarget
from disco_port.serialized_platform import retag_serialized
from disco_port.build_inputs import validate_sources
from disco_port.bundle_validation import bundle_bodies
from disco_port.shader_registry import merge_builtin_registry,disabled_android_builtin
from UnityPy.helpers import CompressionHelper

ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT/'reference/Disco.app/Contents/Resources/Data'
OUTPUT=ROOT/'artifacts/android/game-data'


def disable_unportable_builtins(target):
    disabled=[]
    for obj in target.objects.values():
        data=obj.read_typetree();name=data['m_ParsedForm']['m_Name'];reason=disabled_android_builtin(name,obj.path_id)
        if not reason:continue
        # Keep identity/properties for serialized ownership, but do not advertise
        # a supported subshader for macOS video or excluded VR rendering.
        data['m_ParsedForm']['m_SubShaders']=[]
        blob=CompressionHelper.compress_lz4(bytes(4))
        data.update(platforms=[9],offsets=[[0]],compressedLengths=[[len(blob)]],decompressedLengths=[[4]],compressedBlob=blob)
        obj.save_typetree(data);disabled.append({'name':name,'reason':reason})
    return disabled


def adapt_builtin_shaders(output, exported):
    """Merge exact-version Android built-ins while retaining game-only shaders."""
    name='Resources/unity_builtin_extra'
    game=UnityPy.load(str(output/name));host=UnityPy.load(str(exported/name))
    if len(game.files)!=1 or len(host.files)!=1:raise ValueError('Expected single built-in shader files')
    target=next(iter(game.files.values()));donor=next(iter(host.files.values()))
    if target.unity_version!='2020.3.12f1' or donor.unity_version!=target.unity_version:
        raise ValueError('Built-in shader version mismatch')
    if len(target.types)!=1 or target.types[0].class_id!=48:raise ValueError('Unexpected built-in shader type table')
    for obj in donor.objects.values():
        if obj.type.name!='Shader':raise ValueError('Unexpected non-shader built-in')
        data=obj.read_typetree()
        if data['platforms']!=[9]:raise ValueError('Expected GLES3 built-in')
        existing=target.objects.get(obj.path_id)
        if existing:
            if existing.read_typetree()['m_ParsedForm']['m_Name']!=data['m_ParsedForm']['m_Name']:
                raise ValueError('Built-in path ID collision')
        else:
            existing=copy.copy(obj);existing.assets_file=target;existing.type_id=0
            existing.serialized_type=target.types[0];target.objects[obj.path_id]=existing
        existing.save_typetree(data)
    disabled=disable_unportable_builtins(target)
    (output/name).write_bytes(target.save())
    (OUTPUT/'shader-policy.json').write_text(json.dumps({'disabled_builtins':disabled,'scope':'Android builtin selection; no game-specific shader is disabled'},indent=2)+'\n')
    settings=UnityPy.load(str(output/'globalgamemanagers'))
    host_settings=UnityPy.load(str(exported/'globalgamemanagers'))
    def builtin_id(obj):
        ids=[i+1 for i,x in enumerate(obj.assets_file.externals) if x.path==name]
        if len(ids)!=1:raise ValueError('Missing built-in shader ownership')
        return ids[0]
    host_mappers=[o for o in host_settings.objects if o.type.name=='ScriptMapper']
    host_graphics=[o for o in host_settings.objects if o.type.name=='GraphicsSettings']
    if len(host_mappers)!=1 or len(host_graphics)!=1:raise ValueError('Missing Android shader registry/settings')
    donor_registry=host_mappers[0].read_typetree()['m_Shaders']['m_ObjectToName']
    shader_names={o.path_id:o.read_typetree()['m_ParsedForm']['m_Name'] for o in donor.objects.values()}
    defines=host_graphics[0].read_typetree()['m_ShaderDefinesPerShaderCompiler']
    if len(defines)!=1 or defines[0]['shaderPlatform']!=9:raise ValueError('Expected GLES3 shader defines')
    counts={'ScriptMapper':0,'GraphicsSettings':0}
    for obj in settings.objects:
        if obj.type.name not in counts:continue
        counts[obj.type.name]+=1
        data=obj.read_typetree()
        if obj.type.name=='ScriptMapper':
            data['m_Shaders']['m_ObjectToName']=merge_builtin_registry(
                data['m_Shaders']['m_ObjectToName'],donor_registry,builtin_id(host_mappers[0]),builtin_id(obj),shader_names)
        else:
            ptr={'m_FileID':builtin_id(obj),'m_PathID':16003}
            if ptr not in data['m_AlwaysIncludedShaders']:data['m_AlwaysIncludedShaders'].append(ptr)
            data['m_ShaderDefinesPerShaderCompiler']=[x for x in data['m_ShaderDefinesPerShaderCompiler'] if x['shaderPlatform']!=9]+defines
        obj.save_typetree(data)
    if list(counts.values())!=[1,1]:raise ValueError('Missing or duplicate shader settings')
    (output/'globalgamemanagers').write_bytes(next(iter(settings.files.values())).save())


def adapt_player_settings(path, exported):
    """Use the exact Android host's graphics API list, retaining game scene IDs."""
    host=UnityPy.load(str(exported/'globalgamemanagers'))
    hosts=[o.read_typetree() for o in host.objects if o.type.name=='BuildSettings']
    if len(hosts)!=1 or hosts[0]['m_GraphicsAPIs']!=[11]:
        raise ValueError('Expected exact GLES3 Android host settings')
    game=UnityPy.load(str(path));counts={'BuildSettings':0,'PlayerSettings':0}
    for obj in game.objects:
        if obj.type.name not in counts:continue
        counts[obj.type.name]+=1;data=obj.read_typetree()
        if obj.type.name=='BuildSettings':data['m_GraphicsAPIs']=[11]
        else:data['defaultScreenOrientation']=3
        obj.save_typetree(data)
    if list(counts.values())!=[1,1]:raise ValueError('Missing or duplicate player/build settings')
    if len(game.files)!=1:raise ValueError('Expected one settings asset')
    path.write_bytes(next(iter(game.files.values())).save())


def stage():
    if UnityPy.__version__!='1.25.4':raise ValueError('Expected UnityPy 1.25.4')
    validate_sources(ROOT/'reference/Disco.app')
    # Only disposable generated trees are replaced. Do not carry experimental
    # files or obsolete paths into a fresh public build.
    for name in ('apk','external'):
        folder=OUTPUT/name
        if folder.is_symlink() or not folder.resolve().is_relative_to((ROOT/'artifacts').resolve()):
            raise ValueError('Generated asset directory escapes artifacts')
        if folder.exists():shutil.rmtree(folder)
    for name in ('manifest.json','derived-manifest.json'):(OUTPUT/name).unlink(missing_ok=True)
    output=OUTPUT/'apk/bin/Data';external=OUTPUT/'external/GameFiles'
    output.mkdir(parents=True,exist_ok=True);external.mkdir(parents=True,exist_ok=True)
    records=[];retagged=0;bundles=0
    for source in sorted(SOURCE.rglob('*')):
        if source.is_symlink():raise ValueError('Unexpected asset symlink')
        if not source.is_file():continue
        relative=source.relative_to(SOURCE)
        if relative.parts[0]=='il2cpp_data':continue
        if relative.parts[0] in ('StreamingAssets','AmplifyTexture'):
            target=external/relative
            if relative.parts[0]=='AmplifyTexture':target=external/'Resources/Data'/relative
            if relative.parts[:3]==('StreamingAssets','AssetBundles','OSX'):
                target=external/'StreamingAssets/AssetBundles/Android'/Path(*relative.parts[3:])
        else:target=output/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        with source.open('rb') as stream:signature=stream.read(8)
        serialized=(len(relative.parts)==1 and re.fullmatch(r'(globalgamemanagers(?:\.assets)?|level\d+|sharedassets\d+\.assets|resources\.assets)',source.name)) or str(relative)=='Resources/unity_builtin_extra'
        if serialized:
            data=source.read_bytes();derived,_=retag_serialized(data,13);target.write_bytes(derived);retagged+=1
        elif signature==b'UnityFS\0':
            data=source.read_bytes();environment=UnityPy.load(data)
            if len(environment.files)!=1:raise ValueError('Expected one UnityFS container')
            bundle=next(iter(environment.files.values()));before=bundle_bodies(bundle,2);children=0
            for child in bundle.files.values():
                if not hasattr(child,'objects'):continue
                if child.header.version!=22 or child.unity_version!='2020.3.12f1' or child._m_target_platform!=2:raise ValueError('Unsupported bundle child')
                child._m_target_platform=13;child.target_platform=BuildTarget.Android;child.mark_changed();children+=1
            if not children:raise ValueError('Bundle has no serialized child')
            derived=bundle.save(packer='lz4');check=next(iter(UnityPy.load(derived).files.values()))
            if bundle_bodies(check,13)!=before:raise ValueError('Retag changed asset bytes')
            target.write_bytes(derived);bundles+=1
        else:shutil.copyfile(source,target)
        records.append({'source':str(relative),'target':str(target.relative_to(OUTPUT)),'bytes':target.stat().st_size,'sha256':hashlib.file_digest(target.open('rb'),'sha256').hexdigest()})
    if retagged!=76:raise ValueError(f'Expected 76 serialized assets, found {retagged}')
    exported=ROOT/'artifacts/android/unity-export/unityLibrary/src/main/assets/bin/Data'
    for name in ('unity default resources','boot.config'):
        shutil.copyfile(exported/name,output/name)
    adapt_player_settings(output/'globalgamemanagers',exported)
    adapt_builtin_shaders(output,exported)
    for record in records:
        target=OUTPUT/record['target'];record['bytes']=target.stat().st_size
        with target.open('rb') as stream:record['sha256']=hashlib.file_digest(stream,'sha256').hexdigest()
    (OUTPUT/'manifest.json').write_text(json.dumps({'scope':'Mac assets retagged for Android; GLES conversion and integrity audit follow','serialized_files':retagged,'bundles':bundles,'files':records},indent=2)+'\n')
    print(f'Staged {len(records)} game files; {retagged} serialized tags and {bundles} bundles adapted.')

if __name__=='__main__':stage()
