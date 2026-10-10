"""Select one IL2CPP provider in the pinned exported Unity iOS project."""

import re

from .binary import FormatError


def binding_registrations(symbols):
    bindings = []
    for symbol in sorted(set(symbols)):
        match = re.fullmatch(r'__Z(\d+)(Register_[A-Za-z0-9_]+)v', symbol)
        if match:
            if int(match.group(1)) != len(match.group(2)):
                raise FormatError('Invalid binding registration symbol length')
            # Clang's explicit asm label is used verbatim on Mach-O.
            bindings.append(symbol)
    if not bindings:
        raise FormatError('No supported Unity binding registrations')
    return bindings


def select_original_provider(project):
    objects = project['objects']
    native_targets = [v for v in objects.values() if v['isa'] == 'PBXNativeTarget']
    targets = {v['name']: v for v in native_targets}
    if len(targets) != len(native_targets):
        raise FormatError('Duplicate Xcode target names')
    if 'UnityFramework' not in targets or 'Unity-iPhone' not in targets:
        raise FormatError('Unsupported Unity Xcode target layout')
    framework = targets['UnityFramework']
    sources = [objects[p] for p in framework['buildPhases'] if objects[p]['isa'] == 'PBXSourcesBuildPhase']
    if len(sources) != 1:
        raise FormatError('Expected one UnityFramework source phase')
    removed, kept = [], []
    registrations = {'Classes/Native/UnityClassRegistration.cpp', 'Classes/Native/UnityICallRegistration.cpp'}
    found = set()
    for item in sources[0]['files']:
        ref = objects[objects[item]['fileRef']]
        path = ref.get('path', '')
        if path.startswith('Classes/Native/') and path not in registrations:
            removed.append(item)
        else:
            kept.append(item)
            if path in registrations:
                found.add(path)
    if not removed or found != registrations:
        raise FormatError('Unsupported generated code/registration layout')
    providers = [(k, v) for k, v in objects.items() if v['isa'] == 'PBXFileReference' and v.get('path') == 'Libraries/libil2cpp.a']
    if len(providers) != 1:
        raise FormatError('Expected exactly one generated IL2CPP provider')
    provider_id, provider = providers[0]
    phases = [objects[p] for p in framework['buildPhases'] if objects[p]['isa'] == 'PBXFrameworksBuildPhase']
    if len(phases) != 1 or sum(objects[f]['fileRef'] == provider_id for f in phases[0]['files']) != 1:
        raise FormatError('IL2CPP provider is not owned by the UnityFramework link phase')
    options = [(k, v) for k, v in objects.items() if v['isa'] == 'PBXFileReference' and v.get('path') == 'Il2CppOptions.cpp']
    if len(options) != 1:
        raise FormatError('Expected one runtime options source')
    options_id, options_ref = options[0]
    if sum(objects[f]['fileRef'] == options_id for f in sources[0]['files']) != 1:
        raise FormatError('Runtime options source is not owned by UnityFramework')
    app_configs = objects[targets['Unity-iPhone']['buildConfigurationList']]
    framework_configs = objects[framework['buildConfigurationList']]
    configurations = app_configs['buildConfigurations'] + framework_configs['buildConfigurations']
    if not configurations or any(objects[c]['isa'] != 'XCBuildConfiguration' or
                                 not isinstance(objects[c].get('buildSettings'), dict) for c in configurations):
        raise FormatError('Unsupported Xcode build configuration layout')
    embed_file, embed_phase = 'D15C00000000000000000001', 'D15C00000000000000000002'
    if embed_file in objects or embed_phase in objects:
        raise FormatError('Native engine probe already staged')
    # Validate the complete layout before changing its provider or source phase.
    sources[0]['files'] = kept
    provider.update(path='Frameworks/GameAssembly.framework', name='GameAssembly.framework', lastKnownFileType='wrapper.framework')
    provider.pop('explicitFileType', None)
    options_ref.update(path='GameHost.mm', name='GameHost.mm', lastKnownFileType='sourcecode.cpp.objcpp')
    objects[embed_file] = {'isa': 'PBXBuildFile', 'fileRef': provider_id,
                           'settings': {'ATTRIBUTES': ['CodeSignOnCopy', 'RemoveHeadersOnCopy']}}
    objects[embed_phase] = {'isa': 'PBXCopyFilesBuildPhase', 'buildActionMask': '2147483647',
                            'dstPath': '', 'dstSubfolderSpec': '10', 'files': [embed_file],
                            'name': 'Embed original runtime', 'runOnlyForDeploymentPostprocessing': '0'}
    targets['Unity-iPhone']['buildPhases'].append(embed_phase)
    for config in app_configs['buildConfigurations']:
        objects[config]['buildSettings']['PRODUCT_BUNDLE_IDENTIFIER'] = 'org.discoport.engineprobe'
    for config in framework_configs['buildConfigurations']:
        settings = objects[config]['buildSettings']
        paths = settings.get('FRAMEWORK_SEARCH_PATHS', ['$(inherited)'])
        if isinstance(paths, str):
            paths = [paths]
        settings['FRAMEWORK_SEARCH_PATHS'] = paths + ['$(SRCROOT)/Frameworks']
    return len(removed)


def set_app_bundle_identifier(project, identifier):
    """Change only the owning app target; never a framework/shared configuration."""
    if not isinstance(identifier, str) or len(identifier) > 200 or not re.fullmatch(r'[A-Za-z][A-Za-z0-9-]*(?:\.[A-Za-z][A-Za-z0-9-]*)+', identifier):
        raise FormatError('Expected a reverse-DNS app bundle identifier owned by your team')
    objects = project['objects']
    targets = [(key, value) for key, value in objects.items() if value.get('isa') == 'PBXNativeTarget']
    apps = [(key, value) for key, value in targets if value.get('name') == 'Unity-iPhone']
    if len(apps) != 1:
        raise FormatError('Expected exactly one owning Unity app target')
    app_id, app = apps[0]
    configurations = objects[app['buildConfigurationList']]['buildConfigurations']
    if not configurations or len(set(configurations)) != len(configurations):
        raise FormatError('Invalid app configuration ownership')
    # Include project-level configuration lists as well as other targets.
    for key, owner in objects.items():
        if key != app_id and 'buildConfigurationList' in owner:
            if set(configurations) & set(objects[owner['buildConfigurationList']]['buildConfigurations']):
                raise FormatError('App settings are shared with another owner')
    for config in configurations:
        item = objects[config]
        if item.get('isa') != 'XCBuildConfiguration' or not isinstance(item.get('buildSettings'), dict):
            raise FormatError('Unsupported app build configuration')
    for config in configurations:
        objects[config]['buildSettings']['PRODUCT_BUNDLE_IDENTIFIER'] = identifier
