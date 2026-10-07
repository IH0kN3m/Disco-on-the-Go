"""Embed a prepared private framework only in the owned engine app copy phase."""
import re
from .binary import FormatError


def embed_framework(project, name, file_id, build_id):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}', name) or file_id == build_id:
        raise FormatError('Invalid framework identity')
    objects = project.get('objects', {})
    phase_id = 'D15C00000000000000000002'
    phase = objects.get(phase_id, {})
    owners = [o for o in objects.values() if o.get('isa') == 'PBXNativeTarget' and phase_id in o.get('buildPhases', [])]
    if phase.get('isa') != 'PBXCopyFilesBuildPhase' or phase.get('dstSubfolderSpec') != '10' or len(owners) != 1:
        raise FormatError('Framework copy phase is not owned by one app target')
    if owners[0].get('productType') != 'com.apple.product-type.application' or not isinstance(phase.get('files'), list):
        raise FormatError('Framework copy phase is not an app phase')
    file = {'isa':'PBXFileReference', 'lastKnownFileType':'wrapper.framework',
            'path':'Frameworks/'+name+'.framework', 'sourceTree':'SOURCE_ROOT'}
    build = {'isa':'PBXBuildFile', 'fileRef':file_id,
             'settings':{'ATTRIBUTES':['CodeSignOnCopy','RemoveHeadersOnCopy']}}
    if file_id in objects or build_id in objects:
        if objects.get(file_id) != file or objects.get(build_id) != build or phase['files'].count(build_id) != 1:
            raise FormatError('Conflicting embedded framework identity')
        return
    if any(o.get('path') == file['path'] for o in objects.values()):
        raise FormatError('Framework already belongs to another identity')
    objects[file_id] = file; objects[build_id] = build; phase['files'].append(build_id)


def link_game_controller(project):
    """Link the SDK framework only to the single owned Unity engine target."""
    objects = project.get('objects', {})
    targets = [o for o in objects.values() if o.get('isa') == 'PBXNativeTarget' and o.get('name') == 'UnityFramework']
    if len(targets) != 1 or targets[0].get('productType') != 'com.apple.product-type.framework':
        raise FormatError('GameController requires the owned engine framework target')
    phases = [objects.get(i, {}) for i in targets[0].get('buildPhases', [])
              if objects.get(i, {}).get('isa') == 'PBXFrameworksBuildPhase']
    if len(phases) != 1 or not isinstance(phases[0].get('files'), list):
        raise FormatError('Ambiguous engine framework linkage phase')
    phase = phases[0]
    owners = [o for o in objects.values() if o.get('isa') == 'PBXNativeTarget' and
              any(objects.get(i) is phase for i in o.get('buildPhases', []))]
    if len(owners) != 1:
        raise FormatError('Engine framework phase has multiple owners')
    file_id, build_id = 'D15C00000000000000000060', 'D15C00000000000000000061'
    file = {'isa': 'PBXFileReference', 'lastKnownFileType': 'wrapper.framework',
            'name': 'GameController.framework', 'path': 'System/Library/Frameworks/GameController.framework', 'sourceTree': 'SDKROOT'}
    build = {'isa': 'PBXBuildFile', 'fileRef': file_id}
    if file_id in objects or build_id in objects:
        if objects.get(file_id) != file or objects.get(build_id) != build or phase['files'].count(build_id) != 1:
            raise FormatError('Conflicting GameController framework identity')
        return
    if any(o.get('path') == file['path'] for o in objects.values()):
        raise FormatError('GameController framework already belongs to another identity')
    objects[file_id] = file; objects[build_id] = build; phase['files'].append(build_id)
