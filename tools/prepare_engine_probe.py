#!/usr/bin/env python3
"""Stage a device-only Unity engine experiment with the original IL2CPP provider."""

import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import re
import shutil
import subprocess

from disco_port.build_inputs import validate_sources
from disco_port.engine_project import binding_registrations, select_original_provider
from disco_port.serialized_platform import retag_serialized
from disco_port.plugin_project import link_game_controller

ROOT = Path(__file__).resolve().parent.parent


def prepare(game_data=False, retag=False):
    validate_sources(ROOT / 'reference/Disco.app')
    if retag and not game_data:
        raise ValueError('Serialized loader retagging requires --game-data')
    version = (ROOT / 'artifacts/recovered-unity/ProjectSettings/ProjectVersion.txt').read_text()
    if 'm_EditorVersion: 2020.3.12f1\n' not in version:
        raise ValueError('Engine probe requires the pinned Unity 2020.3.12f1 project')
    source = ROOT / 'artifacts/build/unity-ios'
    output = ROOT / 'artifacts/build/native-engine-ios'
    inputs = ROOT / 'artifacts/runtime-probe'
    report = json.loads((inputs / 'preparation.json').read_text())
    binary = inputs / 'GameAssembly.framework/GameAssembly'
    metadata = inputs / 'NativeMetadata/Metadata/global-metadata.dat'
    for path, digest in ((binary, report['derived_sha256']), (metadata, report['metadata_sha256'])):
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('Prepared native inputs changed; prepare the CPU probe again')
    raw = subprocess.run(['plutil', '-convert', 'json', '-o', '-', str(source / 'Unity-iPhone.xcodeproj/project.pbxproj')],
                         capture_output=True, check=True).stdout
    project = json.loads(raw)
    removed = select_original_provider(project)
    link_game_controller(project)
    nm = subprocess.run(['xcrun', 'nm', '-g', str(source / 'Libraries/libiPhone-lib.a')], capture_output=True, check=True)
    symbols = {line.split()[-1] for line in nm.stdout.decode().splitlines()
               if len(line.split()) == 3 and line.split()[1] in ('T', 'W')}
    registrations = binding_registrations(symbols)
    class_symbols = ('__Z26RegisterAllClassesGranularv', '__Z37RegisterStaticallyLinkedModuleClassesv')
    if not all(symbol in symbols for symbol in class_symbols):
        raise ValueError('The iOS engine lacks full class registration entry points')
    modules = sorted(symbol for symbol in symbols if symbol.startswith('_RegisterModule_'))
    if not modules or any(not re.fullmatch(r'_RegisterModule_[A-Za-z0-9_]+', symbol) for symbol in modules):
        raise ValueError('Unsupported iOS module registration symbols')
    modules.sort(key=lambda name: (name != '_RegisterModule_SharedInternals', name != '_RegisterModule_Core', name))
    # Derived sources and binary listings remain ignored, alongside the export.
    output.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, output, dirs_exist_ok=True,
                    ignore=lambda directory, names: ['Data'] if Path(directory) == source else [])
    data_root = output / 'Data'
    if data_root.exists():
        shutil.rmtree(data_root)
    selected_data = ROOT / 'reference/Disco.app/Contents/Resources/Data' if game_data else source / 'Data'
    shutil.copytree(selected_data, data_root)
    retagged = []
    if game_data:
        shutil.copyfile(source / 'Data/unity default resources', data_root / 'unity default resources')
        streaming = data_root / 'StreamingAssets'
        if not (streaming / 'AssetBundles/OSX').is_dir() or (data_root / 'Raw').exists():
            raise ValueError('Unsupported supplied streaming-assets layout')
        streaming.rename(data_root / 'Raw')
        (data_root / 'Raw/AssetBundles/OSX').rename(data_root / 'Raw/AssetBundles/iOS')
        virtual = data_root / 'AmplifyTexture'
        destination = data_root / 'Resources/Data/AmplifyTexture'
        destination.parent.mkdir(parents=True, exist_ok=True)
        virtual.rename(destination)
    if retag:
        candidates = [p for p in data_root.iterdir() if p.is_file() and
                      (re.fullmatch(r'(globalgamemanagers(?:\.assets)?|level\d+|sharedassets\d+\.assets|resources\.assets)', p.name))]
        candidates.append(data_root / 'Resources/unity_builtin_extra')
        for path in sorted(candidates):
            data = path.read_bytes()
            derived, offset = retag_serialized(data)
            path.write_bytes(derived)
            retagged.append({'path': str(path.relative_to(data_root)), 'offset': offset,
                             'source_sha256': hashlib.sha256(data).hexdigest(), 'derived_sha256': hashlib.sha256(derived).hexdigest()})
    framework = output / 'Frameworks/GameAssembly.framework'
    shutil.copytree(inputs / 'GameAssembly.framework', framework, dirs_exist_ok=True)
    steam = ROOT / 'artifacts/native-plugins/SteamAPI.framework'
    if steam.exists():
        plugin_report = json.loads((steam.parent / 'preparation.json').read_text())
        if hashlib.sha256((steam / 'SteamAPI').read_bytes()).hexdigest() != plugin_report['derived_sha256']:
            raise ValueError('Prepared Steam plugin changed')
        shutil.copytree(steam, output / 'Frameworks/SteamAPI.framework', dirs_exist_ok=True)
        objects = project['objects']
        file_id, build_id = 'D15C00000000000000000003', 'D15C00000000000000000004'
        if file_id in objects or build_id in objects:
            raise ValueError('Plugin already staged')
        objects[file_id] = {'isa': 'PBXFileReference', 'lastKnownFileType': 'wrapper.framework',
                            'path': 'Frameworks/SteamAPI.framework', 'sourceTree': 'SOURCE_ROOT'}
        objects[build_id] = {'isa': 'PBXBuildFile', 'fileRef': file_id, 'settings': {'ATTRIBUTES': ['CodeSignOnCopy', 'RemoveHeadersOnCopy']}}
        objects['D15C00000000000000000002']['files'].append(build_id)
    # Unity's iOS player uses Data/Managed/Metadata; preserve the original runtime's
    # desktop-compatible path as well until the actual engine loader is observed.
    for relative in ('Data/Managed/Metadata/global-metadata.dat', 'Data/il2cpp_data/Metadata/global-metadata.dat'):
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(metadata, destination)
    shutil.copyfile(ROOT / 'reference/Disco.app/Contents/Resources/Data/ScriptingAssemblies.json',
                    output / 'Data/ScriptingAssemblies.json')
    shutil.copyfile(ROOT / 'runtime/UnityHost/iOS/NativeEngineProbe.mm', output / 'Libraries/NativeEngineProbe.mm')
    shutil.copyfile(ROOT / 'runtime/UnityHost/iOS/DiscoSceneResidency.h', output / 'Libraries/DiscoSceneResidency.h')
    shutil.copyfile(ROOT / 'runtime/UnityHost/SceneLoadPolicy.h', output / 'Libraries/SceneLoadPolicy.h')
    shutil.copyfile(ROOT / 'runtime/UnityHost/iOS/DiscoGameDisplay.h', output / 'Libraries/DiscoGameDisplay.h')
    shutil.copyfile(ROOT / 'runtime/UnityHost/DisplayProfile.h', output / 'Libraries/DisplayProfile.h')
    shutil.copyfile(ROOT / 'runtime/UnityHost/iOS/DiscoTouchControls.h', output / 'Libraries/DiscoTouchControls.h')
    shutil.copyfile(ROOT / 'runtime/UnityHost/TouchControlPolicy.h', output / 'Libraries/TouchControlPolicy.h')
    lines = [f'extern "C" void binding_{i}() asm("{symbol}");' for i, symbol in enumerate(registrations)]
    lines.append('void RegisterAllStrippedInternalCalls() {')
    lines.extend(f'    binding_{i}();' for i in range(len(registrations)))
    lines.append('}')
    (output / 'Classes/Native/UnityICallRegistration.cpp').write_text('\n'.join(lines) + '\n')
    classes = [f'extern "C" void native_module_{i}() asm("{symbol}");' for i, symbol in enumerate(modules)]
    classes.extend(['extern "C" void native_classes() asm("__Z26RegisterAllClassesGranularv");',
                    'extern "C" void native_module_classes() asm("__Z37RegisterStaticallyLinkedModuleClassesv");',
                    'extern "C" void RegisterStaticallyLinkedModulesGranular() {'])
    classes.extend(f'    native_module_{i}();' for i in range(len(modules)))
    classes.extend(['}', 'void RegisterAllClasses() { native_classes(); }',
                    'void InvokeRegisterStaticallyLinkedModuleClasses() { native_module_classes(); }'])
    (output / 'Classes/Native/UnityClassRegistration.cpp').write_text('\n'.join(classes) + '\n')
    (output / 'Unity-iPhone.xcodeproj/project.pbxproj').write_bytes(plistlib.dumps(project))
    main = output / 'Classes/main.mm'
    text = main.read_text()
    needle = '    UnityInitTrampoline();\n    UnityInitRuntime(argc, argv);'
    if text.count(needle) != 1:
        raise ValueError('Unsupported Unity runtime startup layout')
    text = 'extern "C" void DiscoNativeEngineBegin();\nextern "C" void DiscoNativeEngineStage(const char*);\n' + text
    text = text.replace(needle, '    DiscoNativeEngineBegin();\n' + needle + '\n    DiscoNativeEngineStage("UnityInitRuntime returned");')
    main.write_text(text)
    controller = output / 'Classes/UnityAppController.mm'
    text = controller.read_text()
    for needle in ('    UnityInitApplicationNoGraphics(UnityDataBundleDir());', '    UnityLoadApplication();'):
        if text.count(needle) != 1:
            raise ValueError('Unsupported Unity application startup layout')
    if text.count('UnityUpdateMuteState(') != 3:
        raise ValueError('Unsupported iOS mute callback layout')
    if text.count('    UnityLowMemory();') != 1:
        raise ValueError('Unsupported iOS memory warning callback layout')
    text = 'extern "C" void DiscoNativeEngineMemoryWarning();\n' + text.replace('    UnityLowMemory();', '    DiscoNativeEngineMemoryWarning();\n    UnityLowMemory();')
    text = text.replace('UnityUpdateMuteState(', 'DiscoUpdateMuteState(')
    text = 'extern "C" void DiscoNativeEngineStage(const char*);\nextern "C" void DiscoNativeEngineLoaded();\nextern "C" void DiscoUpdateMuteState(int);\n' + text
    text = text.replace('    UnityInitApplicationNoGraphics(UnityDataBundleDir());',
                        '    DiscoNativeEngineStage("before UnityInitApplicationNoGraphics");\n    UnityInitApplicationNoGraphics(UnityDataBundleDir());\n    DiscoNativeEngineStage("UnityInitApplicationNoGraphics returned");')
    text = text.replace('    UnityLoadApplication();', '    DiscoNativeEngineStage("before UnityLoadApplication");\n    UnityLoadApplication();\n    DiscoNativeEngineLoaded();')
    text = 'extern "C" void DiscoNativeEnginePlugins();\n' + text
    text = text.replace('    UnityLoadApplication();', '    DiscoNativeEnginePlugins();\n    UnityLoadApplication();')
    controller.write_text(text)
    info = plistlib.loads((output / 'Info.plist').read_bytes())
    info['CFBundleDisplayName'] = 'Disco Engine Lab'
    (output / 'Info.plist').write_bytes(plistlib.dumps(info))
    staging = {'scope': 'Original runtime + iOS engine experiment; original game data' if game_data else 'Original runtime + iOS engine diagnostic; exported diagnostic data, no original gameplay scenes',
               'removed_generated_sources': removed, 'binding_registrations': len(registrations),
               'modules': len(modules), 'original_game_data': game_data,
               'retagged_serialized_files': retagged,
               'source_module_sha256': report['source_sha256'], 'metadata_sha256': report['metadata_sha256']}
    (output / 'native-engine-staging.json').write_text(json.dumps(staging, indent=2) + '\n')
    (output / 'engine-symbols.txt').write_bytes(nm.stdout)
    print(f'Staged original runtime, {len(registrations)} iOS bindings; removed {removed} generated managed sources.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-data', action='store_true', help='Include the complete supplied game data for a startup experiment')
    parser.add_argument('--retag-serialized', action='store_true', help='Experimentally retag derived root serialized files; shader/texture contents remain unconverted')
    args = parser.parse_args()
    try:
        prepare(args.game_data, args.retag_serialized)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        raise SystemExit(f'Engine preparation failed: {error}')
