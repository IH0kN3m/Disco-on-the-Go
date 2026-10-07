"""Validate the recovered transform hierarchy before staging a Unity diagnostic."""

import math

from .binary import FormatError


def index_owned_components(records, type_name, game_objects):
    result = {}
    for record in records:
        if record["type"] != type_name:
            continue
        pointer = record["data"]["m_GameObject"]
        owner = pointer["m_PathID"]
        if type(pointer["m_FileID"]) is not int or pointer["m_FileID"] != 0 or type(owner) is not int or owner not in game_objects:
            raise FormatError(f"{type_name} has unresolved local GameObject ownership")
        if owner in result:
            raise FormatError(f"GameObject has multiple {type_name} components")
        result[owner] = record["data"]
    return result


def flatten_normals(normals, vertex_count):
    if normals is None or normals == []:
        return []
    if not isinstance(normals, (list, tuple)) or len(normals) != vertex_count:
        raise FormatError("Recovered normal count disagrees with vertices")
    result = []
    for normal in normals:
        if not isinstance(normal, (list, tuple)) or len(normal) < 3 or not all(type(v) in (int, float) and math.isfinite(v) for v in normal[:3]):
            raise FormatError("Invalid recovered mesh normal")
        result.extend(normal[:3])
    return result


def validate_parents(parents):
    for identifier, parent in parents.items():
        if parent is not None and parent not in parents:
            raise FormatError(f"Transform {identifier} has an unresolved parent {parent}")
    visited = set()
    for identifier in parents:
        chain = set()
        current = identifier
        while current is not None and current not in visited:
            if current in chain:
                raise FormatError("Recovered transform hierarchy contains a cycle")
            chain.add(current)
            current = parents[current]
        visited.update(chain)


def modernize_ios_project(text):
    """Remove the exact obsolete flags emitted by our pinned Unity exporter."""
    thumb = '\t\t\t\t\t"-mno-thumb",\n'
    if text.count(thumb) != 4:
        raise ValueError("Unsupported Unity Xcode layout: expected four legacy Thumb flags")
    text = text.replace(thumb, "")
    if "-mno-thumb" in text:
        raise ValueError("Unsupported Unity Xcode layout: additional Thumb flags")
    return text.replace("ENABLE_BITCODE = YES;", "ENABLE_BITCODE = NO;")


def modernize_ios_trampoline(text, adapter):
    startup = '- (BOOL)application:(UIApplication*)application didFinishLaunchingWithOptions:(NSDictionary*)launchOptions'
    window = '_window         = [[UIWindow alloc] initWithFrame: [UIScreen mainScreen].bounds];'
    if text.count(startup) != 1 or text.count(window) != 1 or 'discoStartWithScene:' in text:
        raise ValueError("Unsupported Unity iOS startup layout")
    text = text.replace(startup, '- (BOOL)discoStartWithScene:(UIWindowScene*)scene application:(UIApplication*)application launchOptions:(NSDictionary*)launchOptions')
    text = text.replace(window, '_window         = [[UIWindow alloc] initWithWindowScene: scene];')
    return text + '\n' + adapter
def modernize_orientation_transition(text):
    """Update the delegate's controller before UIKit queries its orientation mask."""
    old = '    _rootController = _window.rootViewController = vc;'
    new = '    _rootController = vc;\n    _window.rootViewController = vc;'
    if new in text:
        if text.count(new) != 1 or old in text:
            raise ValueError('Ambiguous modern controller transition')
        return text
    if text.count(old) != 1:
        raise ValueError('Unsupported pinned controller transition')
    return text.replace(old, new)
