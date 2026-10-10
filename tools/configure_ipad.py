#!/usr/bin/env python3
"""Select persistent app-container assets in an already staged engine experiment."""

import hashlib
import argparse
import json
from pathlib import Path
import plistlib
import shutil

from disco_port.device_assets import data_manifest, manifest_bytes
from disco_port.persistent_project import persistent_filesystem, select_persistent_assets, select_increased_memory
from disco_port.unity_stage import modernize_orientation_transition
from disco_port.plugin_project import link_game_controller

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT / 'artifacts/build/native-engine-ios'


def configure(increased_memory=False, debug_memory=None, amplify_cpu=False, lazy_scenes=None, landscape=None):
    staging_path = PROJECT / 'native-engine-staging.json'
    staging = json.loads(staging_path.read_text())
    if staging.get('original_game_data') is not True or len(staging.get('retagged_serialized_files', [])) != 76:
        raise ValueError('Persistent mode requires the complete retagged game experiment')
    manifest = manifest_bytes(data_manifest(PROJECT / 'Data'))
    digest = hashlib.sha256(manifest).hexdigest()
    project_path = PROJECT / 'Unity-iPhone.xcodeproj/project.pbxproj'
    project = plistlib.loads(project_path.read_bytes())
    link_game_controller(project)
    hosts=[v for v in project['objects'].values() if v.get('isa')=='PBXFileReference' and v.get('path') in ('NativeEngineProbe.mm','GameHost.mm')]
    if len(hosts)!=1:raise ValueError('Expected one owning iPad game host source')
    hosts[0].update(path='GameHost.mm',name='GameHost.mm')
    project_path.write_bytes(plistlib.dumps(project))
    if amplify_cpu:
        from prepare_amplify_plugin import stage
        project = plistlib.loads(project_path.read_bytes())
        stage(project, PROJECT)
        project_path.write_bytes(plistlib.dumps(project))
        staging['amplify_cpu'] = True
    filesystem = PROJECT / 'Classes/Unity/Filesystem.mm'
    controller = PROJECT / 'Classes/UnityAppController.mm'
    handling = PROJECT / 'Classes/UI/UnityAppController+ViewHandling.mm'
    handling.write_text(modernize_orientation_transition(handling.read_text()))
    controller_text = controller.read_text()
    if 'DiscoNativeEngineMemoryWarning' not in controller_text:
        if controller_text.count('    UnityLowMemory();') != 1:
            raise ValueError('Unsupported memory warning callback layout')
        controller_text = 'extern "C" void DiscoNativeEngineMemoryWarning();\n' + controller_text.replace('    UnityLowMemory();', '    DiscoNativeEngineMemoryWarning();\n    UnityLowMemory();')
    if not staging.get('persistent_data'):
        project = plistlib.loads(project_path.read_bytes())
        select_persistent_assets(project)
        text = persistent_filesystem(filesystem.read_text())
        project_path.write_bytes(plistlib.dumps(project))
        filesystem.write_text(text)
    if increased_memory or debug_memory is not None or staging.get('increased_memory'):
        project = plistlib.loads(project_path.read_bytes())
        select_increased_memory(project)
        project_path.write_bytes(plistlib.dumps(project))
        entitlements = {'com.apple.developer.kernel.increased-memory-limit': True,
                        'com.apple.developer.kernel.extended-virtual-addressing': True}
        requested_debug = staging.get('debug_memory', False) if debug_memory is None else debug_memory
        if requested_debug:
            entitlements['com.apple.developer.kernel.increased-debugging-memory-limit'] = True
        staging['debug_memory'] = requested_debug
        (PROJECT / 'EngineMemory.entitlements').write_bytes(plistlib.dumps(entitlements))
        staging['increased_memory'] = True
    # Refresh original diagnostic host independently of the derived game data.
    controller.write_text(controller_text)
    shutil.copyfile(ROOT / 'apps/ipad/GameHost.mm', PROJECT / 'Libraries/GameHost.mm')
    shutil.copyfile(ROOT / 'runtime/UnityHost/iOS/DiscoSceneResidency.h', PROJECT / 'Libraries/DiscoSceneResidency.h')
    shutil.copyfile(ROOT / 'runtime/UnityHost/SceneLoadPolicy.h', PROJECT / 'Libraries/SceneLoadPolicy.h')
    shutil.copyfile(ROOT / 'runtime/UnityHost/iOS/DiscoGameDisplay.h', PROJECT / 'Libraries/DiscoGameDisplay.h')
    shutil.copyfile(ROOT / 'runtime/UnityHost/DisplayProfile.h', PROJECT / 'Libraries/DisplayProfile.h')
    shutil.copyfile(ROOT / 'runtime/UnityHost/iOS/DiscoTouchControls.h', PROJECT / 'Libraries/DiscoTouchControls.h')
    shutil.copyfile(ROOT / 'runtime/UnityHost/TouchControlPolicy.h', PROJECT / 'Libraries/TouchControlPolicy.h')
    shutil.copyfile(ROOT / 'runtime/UnityHost/OverlayPlacement.h', PROJECT / 'Libraries/OverlayPlacement.h')
    shutil.copyfile(ROOT / 'runtime/UnityHost/DialogueTextPolicy.h', PROJECT / 'Libraries/DialogueTextPolicy.h')
    shutil.copyfile(ROOT / 'runtime/UnityHost/iOS/DiscoDialogueText.h', PROJECT / 'Libraries/DiscoDialogueText.h')
    info_path = PROJECT / 'Info.plist'
    info = plistlib.loads(info_path.read_bytes())
    info['DiscoPersistentAssets'] = True
    info.pop('DiscoDiagnostics',None)
    staging.pop('diagnostics',None)
    info['DiscoAssetManifestSHA256'] = digest
    if lazy_scenes is not None:
        info['DiscoLazyScenes'] = lazy_scenes
        staging['lazy_scenes'] = lazy_scenes
    if landscape is not None:
        info['DiscoLandscapeDisplay'] = landscape
        info['DiscoFillViewport'] = landscape
        info['DiscoTouchControls'] = landscape
        info['UISupportedInterfaceOrientations'] = ['UIInterfaceOrientationLandscapeLeft', 'UIInterfaceOrientationLandscapeRight']
        info['UISupportedInterfaceOrientations~ipad'] = list(info['UISupportedInterfaceOrientations'])
        staging['landscape_display'] = landscape
    info_path.write_bytes(plistlib.dumps(info))
    (PROJECT / 'device-assets.json').write_bytes(manifest)
    (PROJECT / 'ready.sha256').write_text(digest)
    staging.update(persistent_data=True, asset_manifest_sha256=digest)
    staging_path.write_text(json.dumps(staging, indent=2) + '\n')
    print('Persistent assets selected and fingerprinted; upload before launching this build.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--increased-memory', action='store_true', help='Request the supported iPadOS higher app memory budget')
    parser.add_argument('--amplify-cpu', action='store_true', help='Embed the prepared original CPU codec plugin with explicit desktop GPU guards')
    scenes = parser.add_mutually_exclusive_group()
    scenes.add_argument('--lazy-scenes', dest='lazy_scenes', action='store_true', default=None,
                        help='Keep on-demand scene loading enabled after launches from the Home Screen')
    scenes.add_argument('--no-lazy-scenes', dest='lazy_scenes', action='store_false')
    display = parser.add_mutually_exclusive_group()
    display.add_argument('--landscape', dest='landscape', action='store_true', default=None,
                         help='Use fixed landscape, full tablet viewport and native touch controls')
    display.add_argument('--no-landscape', dest='landscape', action='store_false')
    debugging = parser.add_mutually_exclusive_group()
    debugging.add_argument('--debug-memory', dest='debug_memory', action='store_true', default=None,
                           help='Also request the development-only memory policy')
    debugging.add_argument('--no-debug-memory', dest='debug_memory', action='store_false',
                           help='Use increased memory and extended addressing without the debugging memory policy')
    args = parser.parse_args()
    try:
        configure(args.increased_memory, args.debug_memory, args.amplify_cpu, args.lazy_scenes, args.landscape)
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit(f'Persistent asset configuration failed: {error}')
