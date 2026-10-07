"""Bounded changes to the pinned Unity export's asset ownership and host path."""

from .binary import FormatError


def select_persistent_assets(project):
    objects = project['objects']
    targets = [v for v in objects.values() if v['isa'] == 'PBXNativeTarget']
    apps = [v for v in targets if v['name'] == 'Unity-iPhone']
    engines = [v for v in targets if v['name'] == 'UnityFramework']
    refs = [k for k, v in objects.items() if v['isa'] == 'PBXFileReference' and v.get('path') == 'Data']
    if len(apps) != 1 or len(engines) != 1 or len(refs) != 1:
        raise FormatError('Unsupported persistent asset project layout')
    owners = []
    for target in targets:
        for phase_id in target['buildPhases']:
            phase = objects[phase_id]
            for file_id in phase.get('files', []):
                if objects[file_id].get('fileRef') == refs[0]:
                    owners.append((target, phase, file_id))
    if len(owners) != 1 or owners[0][0] is not apps[0] or owners[0][1]['isa'] != 'PBXResourcesBuildPhase':
        raise FormatError('Expected Data to belong only to app resources')
    configs = objects[engines[0]['buildConfigurationList']]['buildConfigurations']
    settings = [objects[c]['buildSettings'] for c in configs]
    if not settings or any(not isinstance(s, dict) for s in settings):
        raise FormatError('Unsupported engine configurations')
    definitions = []
    for setting in settings:
        existing = setting.get('GCC_PREPROCESSOR_DEFINITIONS', ['$(inherited)'])
        if not isinstance(existing, list) or any(not isinstance(x, str) for x in existing):
            raise FormatError('Unsupported engine preprocessor definitions')
        if any('DISCO_PERSISTENT_DATA' in x for x in existing):
            raise FormatError('Persistent data already selected')
        definitions.append(existing + ['DISCO_PERSISTENT_DATA=1'])
    owners[0][1]['files'].remove(owners[0][2])
    for setting, definition in zip(settings, definitions):
        setting['GCC_PREPROCESSOR_DEFINITIONS'] = definition


def persistent_filesystem(text):
    needle = 'extern "C" const char* UnityDataBundleDir()\n{\n'
    if text.count(needle) != 1 or 'DiscoNativeEngineDataRoot' in text:
        raise FormatError('Unsupported Unity filesystem hook layout')
    return ('extern "C" const char* DiscoNativeEngineDataRoot();\n' +
            text.replace(needle, needle + '#if DISCO_PERSISTENT_DATA\n    return DiscoNativeEngineDataRoot();\n#endif\n'))


def select_increased_memory(project):
    objects = project['objects']
    apps = [v for v in objects.values() if v['isa'] == 'PBXNativeTarget' and v['name'] == 'Unity-iPhone']
    if len(apps) != 1:
        raise FormatError('Expected one app target for memory entitlement')
    configs = objects[apps[0]['buildConfigurationList']]['buildConfigurations']
    settings = [objects[c]['buildSettings'] for c in configs]
    if not settings or any(not isinstance(s, dict) or s.get('CODE_SIGN_ENTITLEMENTS', 'EngineMemory.entitlements') != 'EngineMemory.entitlements' for s in settings):
        raise FormatError('Unexpected app entitlements ownership')
    for setting in settings:
        setting['CODE_SIGN_ENTITLEMENTS'] = 'EngineMemory.entitlements'
